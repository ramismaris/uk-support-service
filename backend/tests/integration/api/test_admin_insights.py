import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.constants import SenderType, TicketStatus, TicketType, UserRole
from src.core.exceptions import LlmException
from src.core.security import hash_token
from src.main import app
from src.providers.factory import get_llm_provider
from src.providers.llm_provider import LlmProvider
from src.repositories.auth_token_repository import AuthTokenRepository
from src.repositories.building_repository import BuildingRepository
from src.repositories.category_repository import CategoryRepository
from src.repositories.message_repository import MessageRepository
from src.repositories.ticket_repository import TicketRepository
from src.repositories.user_repository import UserRepository
from src.services.insights_service import insights_cache

PATH = "/api/v1/admin/dashboard/insights"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _answer(text: str, kind: str = "fact") -> str:
    return json.dumps({"items": [{"kind": kind, "text": text}]}, ensure_ascii=False)


class FakeLlm(LlmProvider):
    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.error: Exception | None = None
        self.calls = 0
        self.prompts: list[tuple[str, str]] = []

    async def complete_json(self, system: str, user: str) -> str:
        self.calls += 1
        self.prompts.append((system, user))
        if self.error is not None:
            raise self.error
        return self.answer


@pytest.fixture(autouse=True)
def clean_insights_cache():
    insights_cache.clear()
    yield
    insights_cache.clear()


@pytest.fixture
def fake_llm() -> FakeLlm:
    provider = FakeLlm(_answer("[[m1]] закрыл 5 заявок."))
    app.dependency_overrides[get_llm_provider] = lambda: provider
    return provider


async def _issue_token(db: AsyncSession, user, *, label: str) -> str:
    token = f"insights-token-{user.id}-{label}"
    await AuthTokenRepository(db).create(
        user.id, hash_token(token), datetime.now(UTC) + timedelta(days=1)
    )
    return token


@pytest.fixture
async def base(db: AsyncSession) -> SimpleNamespace:
    users = UserRepository(db)
    client = await users.create(max_user_id=2000101, first_name="Мария")
    manager = await users.create(max_user_id=2000102, first_name="Игорь", role=UserRole.MANAGER)
    admin = await users.create(max_user_id=2000103, first_name="Анна", role=UserRole.ADMIN)

    client_token = await _issue_token(db, client, label="live")
    manager_token = await _issue_token(db, manager, label="live")
    admin_token = await _issue_token(db, admin, label="live")
    await db.commit()

    return SimpleNamespace(
        client=client,
        manager=manager,
        admin=admin,
        client_token=client_token,
        manager_token=manager_token,
        admin_token=admin_token,
    )


MANAGER_ID = 424242


@pytest.fixture
async def scenario(db: AsyncSession, base: SimpleNamespace) -> SimpleNamespace:
    await db.execute(
        text(
            "INSERT INTO users (id, max_user_id, first_name, last_name, role, is_blocked, created_at)"
            " OVERRIDING SYSTEM VALUE"
            " VALUES (:id, :max_user_id, 'Пётр', 'Петров', CAST(:role AS user_role), false, now())"
        ),
        {"id": MANAGER_ID, "max_user_id": 2000200, "role": UserRole.MANAGER.value},
    )
    building = await BuildingRepository(db).create("ул. Ленина, 12")
    category = await CategoryRepository(db).create("🚰 Сантехника", 1)
    now = datetime.now(UTC)

    tickets = TicketRepository(db)
    for _ in range(3):
        ticket = await tickets.create(
            type=TicketType.REQUEST,
            status=TicketStatus.IN_PROGRESS,
            client_id=base.client.id,
            description="секретное описание заявки",
            category_id=category.id,
            building_id=building.id,
            apartment="45",
            assignee_id=MANAGER_ID,
            created_at=now - timedelta(days=1),
        )
    await MessageRepository(db).create(
        ticket.id,
        SenderType.CLIENT,
        text="секретный текст жильца",
        created_at=now - timedelta(hours=2),
    )
    await db.commit()

    return SimpleNamespace(manager_id=MANAGER_ID, building=building, category=category)


async def test_access_control(
    client: AsyncClient, base: SimpleNamespace, fake_llm: FakeLlm
) -> None:
    assert (await client.get(PATH)).status_code == 401
    assert (await client.post(PATH)).status_code == 401

    for token in (base.client_token, base.manager_token):
        assert (await client.get(PATH, headers=_auth(token))).status_code == 403
        assert (await client.post(PATH, headers=_auth(token))).status_code == 403

    assert (await client.get(PATH, headers=_auth(base.admin_token))).status_code == 200
    assert (await client.post(PATH, headers=_auth(base.admin_token))).status_code == 200


@pytest.mark.parametrize("period", [7, 30, 90])
async def test_period_is_returned(
    client: AsyncClient, base: SimpleNamespace, fake_llm: FakeLlm, period: int
) -> None:
    resp = await client.get(PATH, params={"period": period}, headers=_auth(base.admin_token))

    assert resp.status_code == 200
    assert resp.json()["period_days"] == period


async def test_period_defaults_to_30(
    client: AsyncClient, base: SimpleNamespace, fake_llm: FakeLlm
) -> None:
    resp = await client.get(PATH, headers=_auth(base.admin_token))

    assert resp.status_code == 200
    assert resp.json()["period_days"] == 30


@pytest.mark.parametrize("period", [0, 31, "abc", 9223372036854775808])
async def test_invalid_period_is_422_and_never_calls_provider(
    client: AsyncClient, base: SimpleNamespace, fake_llm: FakeLlm, period: object
) -> None:
    for response in (
        await client.get(PATH, params={"period": period}, headers=_auth(base.admin_token)),
        await client.post(PATH, params={"period": period}, headers=_auth(base.admin_token)),
    ):
        assert response.status_code == 422

    assert fake_llm.calls == 0


async def test_disabled_without_llm(client: AsyncClient, base: SimpleNamespace) -> None:
    app.dependency_overrides[get_llm_provider] = lambda: None

    resp = await client.get(PATH, headers=_auth(base.admin_token))

    assert resp.status_code == 200
    assert resp.json() == {
        "status": "disabled",
        "period_days": 30,
        "generated_at": None,
        "items": [],
    }


async def test_disabled_by_flag(
    client: AsyncClient,
    base: SimpleNamespace,
    fake_llm: FakeLlm,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "ai_insights_enabled", False)

    resp = await client.get(PATH, headers=_auth(base.admin_token))

    assert resp.status_code == 200
    assert resp.json()["status"] == "disabled"
    assert resp.json()["items"] == []
    assert fake_llm.calls == 0


async def test_empty_database_is_ok_without_provider(
    client: AsyncClient, base: SimpleNamespace, fake_llm: FakeLlm
) -> None:
    resp = await client.get(PATH, headers=_auth(base.admin_token))

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["items"] == []
    assert body["generated_at"] is not None
    assert fake_llm.calls == 0


async def test_real_path_returns_names_and_hides_private_data(
    client: AsyncClient, base: SimpleNamespace, scenario: SimpleNamespace, fake_llm: FakeLlm
) -> None:
    resp = await client.get(PATH, headers=_auth(base.admin_token))

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "Пётр" in body["items"][0]["text"]
    assert "[[m1]]" not in body["items"][0]["text"]

    system, user = fake_llm.prompts[0]
    assert "Пётр" not in user
    assert "секретный текст жильца" not in user
    assert "секретное описание заявки" not in user
    assert str(scenario.manager_id) not in user
    assert "assignee_id" not in user
    assert "[[m1]]" in system


async def test_cache_serves_get_and_post_refreshes(
    client: AsyncClient, base: SimpleNamespace, scenario: SimpleNamespace, fake_llm: FakeLlm
) -> None:
    first = await client.get(PATH, headers=_auth(base.admin_token))
    second = await client.get(PATH, headers=_auth(base.admin_token))

    assert first.json() == second.json()
    assert fake_llm.calls == 1

    fake_llm.answer = _answer("Пётр работает медленнее остальных: 3 заявки.")
    refreshed = await client.post(PATH, headers=_auth(base.admin_token))

    assert fake_llm.calls == 2
    assert refreshed.json()["items"][0]["text"] == "Пётр работает медленнее остальных: 3 заявки."

    cached = await client.get(PATH, headers=_auth(base.admin_token))

    assert cached.json() == refreshed.json()
    assert fake_llm.calls == 2


async def test_llm_failure_returns_unavailable(
    client: AsyncClient, base: SimpleNamespace, scenario: SimpleNamespace, fake_llm: FakeLlm
) -> None:
    fake_llm.error = LlmException()

    resp = await client.get(PATH, headers=_auth(base.admin_token))

    assert resp.status_code == 200
    assert resp.json()["status"] == "unavailable"
    assert resp.json()["items"] == []


async def test_garbage_answer_returns_unavailable(
    client: AsyncClient, base: SimpleNamespace, scenario: SimpleNamespace, fake_llm: FakeLlm
) -> None:
    fake_llm.answer = "это совсем не JSON"

    resp = await client.get(PATH, headers=_auth(base.admin_token))

    assert resp.status_code == 200
    assert resp.json()["status"] == "unavailable"
    assert resp.json()["items"] == []


async def test_non_admin_does_not_touch_provider(
    client: AsyncClient, base: SimpleNamespace, fake_llm: FakeLlm
) -> None:
    resp = await client.get(PATH, headers=_auth(base.manager_token))

    assert resp.status_code == 403
    assert fake_llm.calls == 0
