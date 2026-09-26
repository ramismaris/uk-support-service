from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import TicketStatus, TicketType, UserRole
from src.core.exceptions import MessengerException
from src.core.security import hash_token
from src.core.texts import REJECT_REASON_REQUIRED, TICKET_NOT_FOUND
from src.main import app
from src.providers.factory import get_messenger_provider
from src.repositories.auth_token_repository import AuthTokenRepository
from src.repositories.building_repository import BuildingRepository
from src.repositories.category_repository import CategoryRepository
from src.repositories.ticket_repository import TicketRepository
from src.repositories.user_repository import UserRepository

NOW = datetime(2026, 9, 25, 12, 0, tzinfo=UTC)


class FakeMessenger:
    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.edited: list[dict] = []

    async def send_message(self, user_id, text, *, buttons=None, files=None, markdown=False):
        self.sent.append({"user_id": user_id, "text": text, "buttons": buttons})
        return f"mid-{len(self.sent)}"

    async def edit_message(self, message_id, text, *, buttons=None, markdown=False) -> None:
        self.edited.append({"message_id": message_id, "text": text})

    async def upload_file(self, data, mime, filename=None):
        raise MessengerException()

    async def download_file(self, url, max_size):
        raise MessengerException()

    async def close(self) -> None:
        return None


@pytest.fixture
def messenger() -> FakeMessenger:
    provider = FakeMessenger()
    app.dependency_overrides[get_messenger_provider] = lambda: provider
    return provider


async def _issue_token(db: AsyncSession, user) -> str:
    token = f"staff-status-token-{user.id}"
    await AuthTokenRepository(db).create(
        user.id, hash_token(token), datetime.now(UTC) + timedelta(days=1)
    )
    return token


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def base(db: AsyncSession) -> SimpleNamespace:
    users = UserRepository(db)
    client = await users.create(max_user_id=3000003, first_name="Мария", phone="+7 (900) 111-11-11")
    manager = await users.create(max_user_id=3000002, first_name="Игорь", role=UserRole.MANAGER)
    admin = await users.create(max_user_id=3000001, first_name="Анна", role=UserRole.ADMIN)

    building = await BuildingRepository(db).create("ул. Ленина, 12")
    category = await CategoryRepository(db).create("Сантехника", 1)

    manager_token = await _issue_token(db, manager)
    admin_token = await _issue_token(db, admin)
    client_token = await _issue_token(db, client)
    await db.commit()

    return SimpleNamespace(
        client=client,
        manager=manager,
        admin=admin,
        building=building,
        category=category,
        manager_token=manager_token,
        admin_token=admin_token,
        client_token=client_token,
    )


async def _create_ticket(
    db: AsyncSession,
    base: SimpleNamespace,
    *,
    status: TicketStatus = TicketStatus.NEW,
    assignee=None,
    closed_at: datetime | None = None,
    status_card_id: str | None = None,
) -> int:
    ticket = await TicketRepository(db).create(
        type=TicketType.REQUEST,
        status=status,
        client_id=base.client.id,
        description="Описание обращения",
        category_id=base.category.id,
        building_id=base.building.id,
        apartment="45",
        contact_phone="+7 (900) 111-11-11",
        assignee_id=assignee.id if assignee else None,
        created_at=NOW,
        closed_at=closed_at,
    )
    if status_card_id is not None:
        ticket.status_message_max_id = status_card_id
    await db.commit()
    return ticket.id


async def _change_status(
    client: AsyncClient,
    ticket_id: int,
    token: str,
    status: TicketStatus,
    *,
    comment: str | None = None,
):
    body: dict[str, str] = {"status": status}
    if comment is not None:
        body["comment"] = comment
    return await client.post(
        f"/api/v1/staff/tickets/{ticket_id}/status", json=body, headers=_auth(token)
    )


async def test_full_cycle_take_wait_close(
    client: AsyncClient,
    db: AsyncSession,
    base: SimpleNamespace,
    messenger: FakeMessenger,
) -> None:
    ticket_id = await _create_ticket(db, base, status_card_id="card-1")

    take = await _change_status(client, ticket_id, base.manager_token, TicketStatus.IN_PROGRESS)
    assert take.status_code == 200
    body = take.json()
    assert body["status"] == TicketStatus.IN_PROGRESS
    assert body["assignee"]["id"] == base.manager.id
    assert [change["to_status"] for change in body["history"]] == [TicketStatus.IN_PROGRESS]
    assert set(body["allowed_statuses"]) == {
        TicketStatus.WAITING_CLIENT,
        TicketStatus.CLOSED,
        TicketStatus.REJECTED,
    }

    wait = await _change_status(client, ticket_id, base.manager_token, TicketStatus.WAITING_CLIENT)
    assert wait.status_code == 200
    body = wait.json()
    assert body["status"] == TicketStatus.WAITING_CLIENT
    assert [change["to_status"] for change in body["history"]] == [
        TicketStatus.IN_PROGRESS,
        TicketStatus.WAITING_CLIENT,
    ]
    assert set(body["allowed_statuses"]) == {TicketStatus.CLOSED, TicketStatus.REJECTED}

    close = await _change_status(client, ticket_id, base.manager_token, TicketStatus.CLOSED)
    assert close.status_code == 200
    body = close.json()
    assert body["status"] == TicketStatus.CLOSED
    assert body["closed_at"] is not None
    assert set(body["allowed_statuses"]) == set()
    assert [change["to_status"] for change in body["history"]] == [
        TicketStatus.IN_PROGRESS,
        TicketStatus.WAITING_CLIENT,
        TicketStatus.CLOSED,
    ]

    assert [message["user_id"] for message in messenger.sent] == [base.client.max_user_id] * 3
    assert "В работе" in messenger.sent[0]["text"]
    assert "Нужен ваш ответ" in messenger.sent[1]["text"]
    assert "Закрыта" in messenger.sent[2]["text"]
    assert "Проблема решена?" in messenger.sent[2]["text"]

    close_buttons = messenger.sent[-1]["buttons"]
    assert close_buttons is not None
    assert [button.text for row in close_buttons for button in row] == ["Да", "Нет"]

    assert {edit["message_id"] for edit in messenger.edited} == {"card-1"}
    assert len(messenger.edited) == 3

    chat = await client.get(
        f"/api/v1/staff/tickets/{ticket_id}/messages", headers=_auth(base.manager_token)
    )
    assert chat.status_code == 200
    messages = chat.json()
    assert [message["sender_type"] for message in messages] == ["SYSTEM"] * 3
    assert [message["text"] for message in messages] == [
        message["text"] for message in messenger.sent
    ]
    assert messages[-1]["author"] is None


async def test_reject_requires_reason(
    client: AsyncClient,
    db: AsyncSession,
    base: SimpleNamespace,
    messenger: FakeMessenger,
) -> None:
    ticket_id = await _create_ticket(db, base)

    missing = await _change_status(client, ticket_id, base.manager_token, TicketStatus.REJECTED)
    assert missing.status_code == 400
    assert missing.json() == {"detail": REJECT_REASON_REQUIRED}

    blank = await _change_status(
        client, ticket_id, base.manager_token, TicketStatus.REJECTED, comment="   "
    )
    assert blank.status_code == 400
    assert blank.json() == {"detail": REJECT_REASON_REQUIRED}

    card = await client.get(f"/api/v1/staff/tickets/{ticket_id}", headers=_auth(base.manager_token))
    assert card.json()["status"] == TicketStatus.NEW
    assert card.json()["history"] == []
    assert messenger.sent == []

    rejected = await _change_status(
        client, ticket_id, base.manager_token, TicketStatus.REJECTED, comment="Не наш профиль"
    )
    assert rejected.status_code == 200
    body = rejected.json()
    assert body["status"] == TicketStatus.REJECTED
    assert body["closed_at"] is not None
    assert body["history"][-1]["comment"] == "Не наш профиль"
    assert "Не наш профиль" in messenger.sent[-1]["text"]


@pytest.mark.parametrize("status", [TicketStatus.CLOSED, TicketStatus.REJECTED])
async def test_reopen_forbidden_for_manager_allowed_for_admin(
    client: AsyncClient,
    db: AsyncSession,
    base: SimpleNamespace,
    messenger: FakeMessenger,
    status: TicketStatus,
) -> None:
    ticket_id = await _create_ticket(db, base, status=status, assignee=base.manager, closed_at=NOW)

    forbidden = await _change_status(
        client, ticket_id, base.manager_token, TicketStatus.IN_PROGRESS
    )
    assert forbidden.status_code == 403
    assert messenger.sent == []

    reopened = await _change_status(client, ticket_id, base.admin_token, TicketStatus.IN_PROGRESS)
    assert reopened.status_code == 200
    body = reopened.json()
    assert body["status"] == TicketStatus.IN_PROGRESS
    assert body["closed_at"] is None
    assert body["assignee"]["id"] == base.manager.id
    assert body["history"][-1]["changed_by"]["id"] == base.admin.id


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (TicketStatus.NEW, TicketStatus.CLOSED),
        (TicketStatus.NEW, TicketStatus.WAITING_CLIENT),
        (TicketStatus.IN_PROGRESS, TicketStatus.NEW),
        (TicketStatus.WAITING_CLIENT, TicketStatus.NEW),
    ],
)
async def test_invalid_transition_returns_409_and_changes_nothing(
    client: AsyncClient,
    db: AsyncSession,
    base: SimpleNamespace,
    messenger: FakeMessenger,
    current: TicketStatus,
    target: TicketStatus,
) -> None:
    ticket_id = await _create_ticket(db, base, status=current, assignee=base.manager)

    resp = await _change_status(client, ticket_id, base.manager_token, target)

    assert resp.status_code == 409
    assert messenger.sent == []

    card = await client.get(f"/api/v1/staff/tickets/{ticket_id}", headers=_auth(base.manager_token))
    assert card.json()["status"] == current
    assert card.json()["history"] == []


@pytest.mark.parametrize(
    ("ticket_status", "manager_allowed", "admin_allowed"),
    [
        (
            TicketStatus.NEW,
            {TicketStatus.IN_PROGRESS, TicketStatus.REJECTED},
            {TicketStatus.IN_PROGRESS, TicketStatus.REJECTED},
        ),
        (
            TicketStatus.IN_PROGRESS,
            {TicketStatus.WAITING_CLIENT, TicketStatus.CLOSED, TicketStatus.REJECTED},
            {TicketStatus.WAITING_CLIENT, TicketStatus.CLOSED, TicketStatus.REJECTED},
        ),
        (
            TicketStatus.WAITING_CLIENT,
            {TicketStatus.CLOSED, TicketStatus.REJECTED},
            {TicketStatus.CLOSED, TicketStatus.REJECTED},
        ),
        (TicketStatus.CLOSED, set(), {TicketStatus.IN_PROGRESS}),
        (TicketStatus.REJECTED, set(), {TicketStatus.IN_PROGRESS}),
    ],
)
async def test_allowed_statuses_in_card_for_manager_and_admin(
    client: AsyncClient,
    db: AsyncSession,
    base: SimpleNamespace,
    ticket_status: TicketStatus,
    manager_allowed: set[TicketStatus],
    admin_allowed: set[TicketStatus],
) -> None:
    ticket_id = await _create_ticket(
        db,
        base,
        status=ticket_status,
        closed_at=NOW if ticket_status in (TicketStatus.CLOSED, TicketStatus.REJECTED) else None,
    )

    manager_resp = await client.get(
        f"/api/v1/staff/tickets/{ticket_id}", headers=_auth(base.manager_token)
    )
    admin_resp = await client.get(
        f"/api/v1/staff/tickets/{ticket_id}", headers=_auth(base.admin_token)
    )

    assert manager_resp.status_code == 200
    assert admin_resp.status_code == 200
    assert set(manager_resp.json()["allowed_statuses"]) == manager_allowed
    assert set(admin_resp.json()["allowed_statuses"]) == admin_allowed


async def test_status_requires_token(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/staff/tickets/1/status", json={"status": TicketStatus.IN_PROGRESS}
    )

    assert resp.status_code == 401


async def test_status_forbidden_for_client(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    ticket_id = await _create_ticket(db, base)

    resp = await _change_status(client, ticket_id, base.client_token, TicketStatus.IN_PROGRESS)

    assert resp.status_code == 403


@pytest.mark.parametrize("ticket_id", [0, 2**63])
async def test_status_rejects_out_of_range_ticket_id(
    client: AsyncClient, base: SimpleNamespace, ticket_id: int
) -> None:
    resp = await _change_status(client, ticket_id, base.manager_token, TicketStatus.IN_PROGRESS)

    assert resp.status_code == 422


async def test_status_rejects_unknown_status_value(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    ticket_id = await _create_ticket(db, base)

    resp = await client.post(
        f"/api/v1/staff/tickets/{ticket_id}/status",
        json={"status": "BOGUS"},
        headers=_auth(base.manager_token),
    )

    assert resp.status_code == 422


async def test_status_unknown_ticket_returns_404(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    resp = await _change_status(client, 999999, base.manager_token, TicketStatus.IN_PROGRESS)

    assert resp.status_code == 404
    assert resp.json() == {"detail": TICKET_NOT_FOUND}
