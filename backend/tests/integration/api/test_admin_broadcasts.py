import re
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import (
    BroadcastStatus,
    TicketStatus,
    TicketType,
    UserRole,
)
from src.core.security import hash_token
from src.core.texts import (
    BROADCAST_IN_PROGRESS,
    BROADCAST_NO_RECIPIENTS,
    BUILDING_NOT_FOUND,
)
from src.main import app
from src.providers.factory import get_storage_provider
from src.providers.local_storage_provider import LocalStorageProvider
from src.repositories.auth_token_repository import AuthTokenRepository
from src.repositories.broadcast_repository import BroadcastRepository
from src.repositories.building_repository import BuildingRepository
from src.repositories.residence_repository import ResidenceRepository
from src.repositories.ticket_repository import TicketRepository
from src.repositories.user_repository import UserRepository
from src.services.file_service import FileService

PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
FILE_URL_PATTERN = re.compile(r"^/api/v1/files/\d+\?exp=\d+&sig=[0-9a-f]{64}$")

AUDIENCE = "/api/v1/admin/broadcasts/audience"
BROADCASTS = "/api/v1/admin/broadcasts"
BUILDINGS = "/api/v1/staff/buildings"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _issue_token(db: AsyncSession, user, label: str) -> str:
    token = f"broadcast-token-{user.id}-{label}"
    await AuthTokenRepository(db).create(
        user.id, hash_token(token), datetime.now(UTC) + timedelta(days=1)
    )
    return token


@contextmanager
def _background():
    with (
        patch("src.services.broadcast_service.run_in_background") as run_bg,
        patch(
            "src.services.broadcast_service.run_broadcast",
            new=MagicMock(return_value="broadcast-coroutine"),
        ) as run_broadcast,
    ):
        yield SimpleNamespace(run_bg=run_bg, run_broadcast=run_broadcast)


@pytest.fixture
def storage(tmp_path) -> LocalStorageProvider:
    provider = LocalStorageProvider(str(tmp_path))
    app.dependency_overrides[get_storage_provider] = lambda: provider
    return provider


@pytest.fixture
async def base(db: AsyncSession) -> SimpleNamespace:
    users = UserRepository(db)
    client = await users.create(max_user_id=5000003, first_name="Мария")
    manager = await users.create(max_user_id=5000002, first_name="Игорь", role=UserRole.MANAGER)
    admin = await users.create(max_user_id=5000001, first_name="Анна", role=UserRole.ADMIN)
    never_seen = await users.create(max_user_id=5000004, first_name="Новичок")
    blocked = await users.create(max_user_id=5000005, first_name="Блок")
    blocked.is_blocked = True
    other_client = await users.create(max_user_id=5000006, first_name="Пётр")

    buildings = BuildingRepository(db)
    building_a = await buildings.create("ул. А, 1")
    building_b = await buildings.create("ул. Б, 1")
    building_inactive = await buildings.create("ул. В, 1")
    building_inactive.is_active = False

    residences = ResidenceRepository(db)
    await residences.create(client.id, building_a.id, "1", is_primary=True)
    await residences.create(other_client.id, building_b.id, "2", is_primary=True)

    now = datetime.now(UTC)
    client.last_seen_at = now
    blocked.last_seen_at = now
    other_client.last_seen_at = now

    client_token = await _issue_token(db, client, "live")
    manager_token = await _issue_token(db, manager, "live")
    admin_token = await _issue_token(db, admin, "live")
    await db.commit()

    return SimpleNamespace(
        client=client,
        manager=manager,
        admin=admin,
        never_seen=never_seen,
        blocked=blocked,
        other_client=other_client,
        building_a=building_a,
        building_b=building_b,
        building_inactive=building_inactive,
        client_token=client_token,
        manager_token=manager_token,
        admin_token=admin_token,
    )


async def _content_image(db: AsyncSession, storage: LocalStorageProvider):
    return await FileService(db, storage).save_image(PNG, "broadcast.png")


def _broadcast_body(**overrides) -> dict:
    body = {"text": "Уважаемые жильцы"}
    body.update(overrides)
    return body


async def _store_broadcast(
    db: AsyncSession,
    author,
    *,
    text: str = "Рассылка",
    buildings: list | None = None,
    file_id: int | None = None,
    recipients_total: int = 1,
    status: BroadcastStatus = BroadcastStatus.DONE,
):
    broadcast = await BroadcastRepository(db).create(
        author_id=author.id,
        text=text,
        file_id=file_id,
        recipients_total=recipients_total,
        buildings=buildings or [],
        status=status,
    )
    await db.commit()
    return broadcast


# --- access control ---

ADMIN_ROUTES = [
    pytest.param("GET", AUDIENCE, None, id="audience"),
    pytest.param("POST", BROADCASTS, {"text": "Привет"}, id="create"),
    pytest.param("GET", BROADCASTS, None, id="history"),
]


async def _call(client: AsyncClient, method: str, path: str, *, headers=None, body=None):
    if method == "GET":
        return await client.get(path, headers=headers)
    return await client.post(path, json=body, headers=headers)


@pytest.mark.parametrize(("method", "path", "body"), ADMIN_ROUTES)
async def test_broadcast_routes_require_token(
    client: AsyncClient, method: str, path: str, body: dict | None
) -> None:
    resp = await _call(client, method, path, body=body)

    assert resp.status_code == 401


@pytest.mark.parametrize("role", ["manager", "client"])
@pytest.mark.parametrize(("method", "path", "body"), ADMIN_ROUTES)
async def test_broadcast_routes_forbidden_for_non_admin(
    client: AsyncClient,
    base: SimpleNamespace,
    role: str,
    method: str,
    path: str,
    body: dict | None,
) -> None:
    token = base.manager_token if role == "manager" else base.client_token

    resp = await _call(client, method, path, headers=_auth(token), body=body)

    assert resp.status_code == 403


# --- audience ---


async def test_audience_all_returns_seen_clients(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    resp = await client.get(AUDIENCE, headers=_auth(base.admin_token))

    assert resp.status_code == 200
    assert resp.json() == {"count": 2}


async def test_audience_by_one_building(client: AsyncClient, base: SimpleNamespace) -> None:
    resp = await client.get(
        AUDIENCE,
        params={"building_id": base.building_a.id},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 200
    assert resp.json() == {"count": 1}


async def test_audience_by_two_buildings_deduplicates(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    # A resident of both chosen buildings is still counted once.
    await ResidenceRepository(db).create(base.client.id, base.building_b.id, "7", is_primary=False)
    await db.commit()

    resp = await client.get(
        AUDIENCE,
        params=[
            ("building_id", base.building_a.id),
            ("building_id", base.building_b.id),
        ],
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 200
    assert resp.json() == {"count": 2}


async def test_audience_without_seen_clients_is_zero(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    for user in (base.client, base.other_client, base.blocked):
        user.last_seen_at = None
    await db.commit()

    resp = await client.get(AUDIENCE, headers=_auth(base.admin_token))

    assert resp.status_code == 200
    assert resp.json() == {"count": 0}


async def test_audience_unknown_building_is_400(client: AsyncClient, base: SimpleNamespace) -> None:
    resp = await client.get(
        AUDIENCE, params={"building_id": 999999}, headers=_auth(base.admin_token)
    )

    assert resp.status_code == 400
    assert resp.json() == {"detail": BUILDING_NOT_FOUND}


async def test_audience_inactive_building_is_400(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    resp = await client.get(
        AUDIENCE,
        params={"building_id": base.building_inactive.id},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 400
    assert resp.json() == {"detail": BUILDING_NOT_FOUND}


@pytest.mark.parametrize("value", [0, -1, "abc", 2**63])
async def test_audience_bad_building_id_is_422(
    client: AsyncClient, base: SimpleNamespace, value
) -> None:
    resp = await client.get(
        AUDIENCE, params={"building_id": value}, headers=_auth(base.admin_token)
    )

    assert resp.status_code == 422


async def test_audience_too_many_building_ids_is_422(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    resp = await client.get(
        AUDIENCE,
        params=[("building_id", value) for value in range(1, 102)],
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 422


# --- create ---


async def test_create_returns_202_with_the_whole_response(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace, storage: LocalStorageProvider
) -> None:
    with _background() as bg:
        resp = await client.post(
            BROADCASTS,
            json={"text": "  Уважаемые жильцы  ", "building_ids": [base.building_a.id]},
            headers=_auth(base.admin_token),
        )

    assert resp.status_code == 202
    body = resp.json()
    assert body["author"] == {"id": base.admin.id, "first_name": "Анна", "last_name": None}
    assert body["text"] == "Уважаемые жильцы"
    assert body["buildings"] == [{"id": base.building_a.id, "address": "ул. А, 1"}]
    assert body["status"] == "SENDING"
    assert body["recipients_total"] == 1
    assert body["delivered_count"] == 0
    assert body["failed_count"] == 0
    assert body["finished_at"] is None
    assert body["created_at"]
    assert body["file_url"] is None
    assert "file_id" not in body

    bg.run_broadcast.assert_called_once_with(body["id"], [base.client.max_user_id])
    bg.run_bg.assert_called_once_with("broadcast-coroutine", name=f"broadcast-{body['id']}")

    stored = await BroadcastRepository(db).get_by_id(body["id"])
    assert stored is not None
    assert stored.author_id == base.admin.id
    assert stored.recipients_total == 1
    assert [building.id for building in stored.buildings] == [base.building_a.id]


async def test_create_lists_buildings_by_address_like_the_history(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace, storage: LocalStorageProvider
) -> None:
    with _background():
        resp = await client.post(
            BROADCASTS,
            json={"text": "Текст", "building_ids": [base.building_b.id, base.building_a.id]},
            headers=_auth(base.admin_token),
        )
    history = await client.get(BROADCASTS, headers=_auth(base.admin_token))

    assert resp.status_code == 202
    created = [building["address"] for building in resp.json()["buildings"]]
    assert created == ["ул. А, 1", "ул. Б, 1"]
    assert [b["address"] for b in history.json()["items"][0]["buildings"]] == created


async def test_create_for_everyone_sends_to_all_recipients(
    client: AsyncClient, base: SimpleNamespace, storage: LocalStorageProvider
) -> None:
    with _background() as bg:
        resp = await client.post(BROADCASTS, json={"text": "Всем"}, headers=_auth(base.admin_token))

    assert resp.status_code == 202
    assert resp.json()["buildings"] == []
    assert resp.json()["recipients_total"] == 2
    bg.run_broadcast.assert_called_once_with(
        resp.json()["id"], [base.client.max_user_id, base.other_client.max_user_id]
    )


async def test_create_with_photo_returns_signed_file_url(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace, storage: LocalStorageProvider
) -> None:
    image = await _content_image(db, storage)

    with _background():
        resp = await client.post(
            BROADCASTS,
            json={"text": "С фото", "file_id": image.id},
            headers=_auth(base.admin_token),
        )

    assert resp.status_code == 202
    body = resp.json()
    assert FILE_URL_PATTERN.match(body["file_url"])
    assert "file_id" not in body


async def test_create_keeps_the_token_author_ignoring_body_author(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace, storage: LocalStorageProvider
) -> None:
    with _background():
        resp = await client.post(
            BROADCASTS,
            json={"text": "Текст", "author_id": base.other_client.id},
            headers=_auth(base.admin_token),
        )

    assert resp.status_code == 202
    assert resp.json()["author"]["id"] == base.admin.id


CREATE_INVALID_BODIES = [
    pytest.param({"text": ""}, id="empty-text"),
    pytest.param({"text": "   "}, id="blank-text"),
    pytest.param({"text": "x" * 3001}, id="text-too-long"),
    pytest.param({"text": "a\x00b"}, id="nul-text"),
    pytest.param({"text": "Текст", "building_ids": []}, id="empty-buildings"),
    pytest.param({"text": "Текст", "building_ids": list(range(1, 102))}, id="too-many-buildings"),
    pytest.param({"text": "Текст", "building_ids": [2**63]}, id="building-too-big"),
    pytest.param({"text": "Текст", "building_ids": [0]}, id="building-zero"),
    pytest.param({"text": "Текст", "file_id": 2**63}, id="file-too-big"),
    pytest.param({"text": "Текст", "file_id": 0}, id="file-zero"),
]


@pytest.mark.parametrize("body", CREATE_INVALID_BODIES)
async def test_create_invalid_body_is_422(
    client: AsyncClient, base: SimpleNamespace, body: dict
) -> None:
    resp = await client.post(BROADCASTS, json=body, headers=_auth(base.admin_token))

    assert resp.status_code == 422


async def test_create_unknown_building_is_400(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace, storage: LocalStorageProvider
) -> None:
    with _background() as bg:
        resp = await client.post(
            BROADCASTS,
            json={"text": "Текст", "building_ids": [999999]},
            headers=_auth(base.admin_token),
        )

    assert resp.status_code == 400
    assert resp.json() == {"detail": BUILDING_NOT_FOUND}
    assert await BroadcastRepository(db).count() == 0
    bg.run_bg.assert_not_called()


async def test_create_inactive_building_is_400(
    client: AsyncClient, base: SimpleNamespace, storage: LocalStorageProvider
) -> None:
    resp = await client.post(
        BROADCASTS,
        json={"text": "Текст", "building_ids": [base.building_inactive.id]},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 400
    assert resp.json() == {"detail": BUILDING_NOT_FOUND}


async def test_create_unknown_file_is_400(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace, storage: LocalStorageProvider
) -> None:
    with _background() as bg:
        resp = await client.post(
            BROADCASTS,
            json={"text": "Текст", "file_id": 999999},
            headers=_auth(base.admin_token),
        )

    assert resp.status_code == 400
    assert await BroadcastRepository(db).count() == 0
    bg.run_bg.assert_not_called()


async def test_create_ticket_attachment_is_400(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace, storage: LocalStorageProvider
) -> None:
    ticket = await TicketRepository(db).create(
        type=TicketType.QUESTION,
        status=TicketStatus.NEW,
        client_id=base.client.id,
        description="Вопрос",
    )
    await db.flush()
    file = await FileService(db, storage).save(
        PNG, "image/png", original_name="photo.png", ticket_id=ticket.id
    )

    with _background() as bg:
        resp = await client.post(
            BROADCASTS,
            json={"text": "Текст", "file_id": file.id},
            headers=_auth(base.admin_token),
        )

    assert resp.status_code == 400
    bg.run_bg.assert_not_called()


async def test_create_without_recipients_is_400_and_saves_nothing(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace, storage: LocalStorageProvider
) -> None:
    for user in (base.client, base.other_client, base.blocked):
        user.last_seen_at = None
    await db.commit()

    with _background() as bg:
        resp = await client.post(
            BROADCASTS, json={"text": "Текст"}, headers=_auth(base.admin_token)
        )

    assert resp.status_code == 400
    assert resp.json() == {"detail": BROADCAST_NO_RECIPIENTS}
    assert await BroadcastRepository(db).count() == 0
    bg.run_bg.assert_not_called()


async def test_second_create_while_sending_is_409(
    client: AsyncClient, base: SimpleNamespace, storage: LocalStorageProvider
) -> None:
    with _background() as bg:
        first = await client.post(
            BROADCASTS, json={"text": "Первая"}, headers=_auth(base.admin_token)
        )
        second = await client.post(
            BROADCASTS, json={"text": "Вторая"}, headers=_auth(base.admin_token)
        )

    assert first.status_code == 202
    assert second.status_code == 409
    assert second.json() == {"detail": BROADCAST_IN_PROGRESS}
    assert bg.run_bg.call_count == 1


# --- history ---


async def test_history_empty_is_zero(client: AsyncClient, base: SimpleNamespace) -> None:
    resp = await client.get(BROADCASTS, headers=_auth(base.admin_token))

    assert resp.status_code == 200
    assert resp.json() == {"total": 0, "items": []}


async def test_history_is_newest_first_and_reports_total(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    first = await _store_broadcast(db, base.admin, text="Первая")
    second = await _store_broadcast(db, base.admin, text="Вторая")
    third = await _store_broadcast(db, base.admin, text="Третья")

    resp = await client.get(BROADCASTS, headers=_auth(base.admin_token))

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert [item["id"] for item in body["items"]] == [third.id, second.id, first.id]


async def test_history_item_exposes_the_spec_fields(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    repo = BroadcastRepository(db)
    sending = await repo.create(
        author_id=base.admin.id,
        text="Идёт рассылка",
        file_id=None,
        recipients_total=5,
        buildings=[],
        status=BroadcastStatus.SENDING,
    )
    await repo.save_progress(sending.id, delivered_count=2, failed_count=1)
    await db.commit()

    resp = await client.get(BROADCASTS, headers=_auth(base.admin_token))

    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert set(item) == {
        "id",
        "author",
        "text",
        "file_url",
        "buildings",
        "status",
        "recipients_total",
        "delivered_count",
        "failed_count",
        "created_at",
        "finished_at",
    }
    assert item["id"] == sending.id
    assert item["author"] == {"id": base.admin.id, "first_name": "Анна", "last_name": None}
    assert item["text"] == "Идёт рассылка"
    assert item["file_url"] is None
    assert item["buildings"] == []
    assert item["status"] == "SENDING"
    assert item["recipients_total"] == 5
    assert item["delivered_count"] == 2
    assert item["failed_count"] == 1
    assert item["created_at"]
    assert item["finished_at"] is None

    await repo.finish(sending.id, BroadcastStatus.DONE)
    await db.commit()

    finished = await client.get(BROADCASTS, headers=_auth(base.admin_token))
    item = finished.json()["items"][0]
    assert item["status"] == "DONE"
    assert item["finished_at"] is not None


async def test_history_buildings_are_ordered_by_address(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    # Passed in reverse order; the response must come back sorted by address.
    await _store_broadcast(
        db, base.admin, text="Двум домам", buildings=[base.building_b, base.building_a]
    )

    resp = await client.get(BROADCASTS, headers=_auth(base.admin_token))

    assert resp.status_code == 200
    assert resp.json()["items"][0]["buildings"] == [
        {"id": base.building_a.id, "address": "ул. А, 1"},
        {"id": base.building_b.id, "address": "ул. Б, 1"},
    ]


async def test_history_photo_has_file_url_and_hides_file_id(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace, storage: LocalStorageProvider
) -> None:
    image = await _content_image(db, storage)
    await _store_broadcast(db, base.admin, text="С фото", file_id=image.id)

    resp = await client.get(BROADCASTS, headers=_auth(base.admin_token))

    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert FILE_URL_PATTERN.match(item["file_url"])
    assert "file_id" not in item


async def test_history_never_exposes_recipients(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    await _store_broadcast(db, base.admin, text="Всем", recipients_total=2)

    resp = await client.get(BROADCASTS, headers=_auth(base.admin_token))

    assert resp.status_code == 200
    assert "max_user_id" not in resp.text
    assert str(base.client.max_user_id) not in resp.text
    assert str(base.other_client.max_user_id) not in resp.text


async def test_history_paginates_with_total(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    first = await _store_broadcast(db, base.admin, text="Первая")
    second = await _store_broadcast(db, base.admin, text="Вторая")
    third = await _store_broadcast(db, base.admin, text="Третья")

    page = await client.get(BROADCASTS, params={"limit": 2}, headers=_auth(base.admin_token))
    assert page.status_code == 200
    assert [item["id"] for item in page.json()["items"]] == [third.id, second.id]
    assert page.json()["total"] == 3

    tail = await client.get(
        BROADCASTS, params={"skip": 2, "limit": 2}, headers=_auth(base.admin_token)
    )
    assert tail.status_code == 200
    assert [item["id"] for item in tail.json()["items"]] == [first.id]
    assert tail.json()["total"] == 3


@pytest.mark.parametrize(
    "params",
    [
        {"skip": 2**63},
        {"skip": -1},
        {"limit": 0},
        {"limit": 101},
        {"limit": "abc"},
    ],
)
async def test_history_bad_pagination_is_422(
    client: AsyncClient, base: SimpleNamespace, params: dict
) -> None:
    resp = await client.get(BROADCASTS, params=params, headers=_auth(base.admin_token))

    assert resp.status_code == 422


# --- ticket attachment shape of the create response ---


async def test_create_response_hides_file_id(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace, storage: LocalStorageProvider
) -> None:
    image = await _content_image(db, storage)

    with _background():
        resp = await client.post(
            BROADCASTS,
            json={"text": "С фото", "file_id": image.id},
            headers=_auth(base.admin_token),
        )

    assert resp.status_code == 202
    assert "file_id" not in resp.json()


# --- staff buildings ---


async def test_staff_buildings_require_token(client: AsyncClient) -> None:
    resp = await client.get(BUILDINGS)

    assert resp.status_code == 401


async def test_staff_buildings_forbidden_for_client(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    resp = await client.get(BUILDINGS, headers=_auth(base.client_token))

    assert resp.status_code == 403


@pytest.mark.parametrize("role", ["manager", "admin"])
async def test_staff_buildings_returns_active_ordered_by_address(
    client: AsyncClient, base: SimpleNamespace, role: str
) -> None:
    token = base.manager_token if role == "manager" else base.admin_token

    resp = await client.get(BUILDINGS, headers=_auth(token))

    assert resp.status_code == 200
    body = resp.json()
    assert body == [
        {"id": base.building_a.id, "address": "ул. А, 1"},
        {"id": base.building_b.id, "address": "ул. Б, 1"},
    ]
    assert {key for building in body for key in building} == {"id", "address"}
