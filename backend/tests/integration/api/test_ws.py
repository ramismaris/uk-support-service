import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import httpx_ws
import pytest
from httpx import AsyncClient
from httpx_ws import aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import SenderType, TicketStatus, TicketType, UserRole
from src.core.exceptions import MessengerException
from src.core.security import hash_token
from src.core.ws_manager import ws_manager
from src.main import app
from src.providers.factory import get_messenger_provider, get_storage_provider
from src.providers.local_storage_provider import LocalStorageProvider
from src.repositories.auth_token_repository import AuthTokenRepository
from src.repositories.building_repository import BuildingRepository
from src.repositories.category_repository import CategoryRepository
from src.repositories.message_repository import MessageRepository
from src.repositories.ticket_repository import TicketRepository
from src.repositories.user_repository import UserRepository

WS_PATH = "/api/v1/ws"
NOW = datetime(2026, 9, 25, 12, 0, tzinfo=UTC)


class FakeMessenger:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_message(self, user_id, text, *, buttons=None, files=None, markdown=False):
        self.sent.append({"user_id": user_id, "text": text})
        return f"mid-{len(self.sent)}"

    async def edit_message(self, message_id, text, *, buttons=None, markdown=False) -> None:
        return None

    async def upload_file(self, data, mime, filename=None):
        return f"tok-{len(self.sent)}"

    async def download_file(self, url, max_size):
        raise MessengerException()

    async def close(self) -> None:
        return None


def _ws_http() -> AsyncClient:
    return AsyncClient(transport=ASGIWebSocketTransport(app), base_url="http://test")


async def _receive_json(ws) -> dict:
    async with asyncio.timeout(5):
        return await ws.receive_json()


async def _wait_until(predicate) -> None:
    async with asyncio.timeout(5):
        while not predicate():
            await asyncio.sleep(0.01)


async def _closed_with(http: AsyncClient, url: str) -> int:
    try:
        async with aconnect_ws(url, http) as ws:
            await _receive_json(ws)
    except httpx_ws.WebSocketDisconnect as exc:
        return exc.code
    except BaseExceptionGroup as group:
        for error in group.exceptions:
            if isinstance(error, httpx_ws.WebSocketDisconnect):
                return error.code
        raise
    raise AssertionError("the server did not close the connection")


@pytest.fixture(autouse=True)
def reset_ws_manager() -> Iterator[None]:
    yield
    ws_manager._connections.clear()


@pytest.fixture
def storage(tmp_path) -> LocalStorageProvider:
    provider = LocalStorageProvider(str(tmp_path))
    app.dependency_overrides[get_storage_provider] = lambda: provider
    return provider


@pytest.fixture
def messenger() -> FakeMessenger:
    provider = FakeMessenger()
    app.dependency_overrides[get_messenger_provider] = lambda: provider
    return provider


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _issue_token(
    db: AsyncSession, user, *, label: str, expires_at: datetime | None = None
) -> str:
    token = f"ws-token-{user.id}-{user.max_user_id}-{label}"
    await AuthTokenRepository(db).create(
        user.id,
        hash_token(token),
        expires_at if expires_at is not None else datetime.now(UTC) + timedelta(days=1),
    )
    return token


@pytest.fixture
async def base(db: AsyncSession) -> SimpleNamespace:
    users = UserRepository(db)
    client = await users.create(max_user_id=3000003, first_name="Мария", phone="+7 (900) 111-11-11")
    manager = await users.create(max_user_id=3000002, first_name="Игорь", role=UserRole.MANAGER)
    blocked = await users.create(max_user_id=3000004, first_name="Пётр", role=UserRole.MANAGER)
    blocked.is_blocked = True
    building = await BuildingRepository(db).create("ул. Ленина, 12")
    category = await CategoryRepository(db).create("Сантехника", 1)

    manager_token = await _issue_token(db, manager, label="live")
    client_token = await _issue_token(db, client, label="live")
    blocked_token = await _issue_token(db, blocked, label="live")
    expired_token = await _issue_token(
        db, manager, label="expired", expires_at=datetime.now(UTC) - timedelta(minutes=1)
    )
    await db.commit()

    return SimpleNamespace(
        client=client,
        manager=manager,
        blocked=blocked,
        building=building,
        category=category,
        manager_token=manager_token,
        client_token=client_token,
        blocked_token=blocked_token,
        expired_token=expired_token,
    )


async def _create_ticket(
    db: AsyncSession, base: SimpleNamespace, *, status: TicketStatus = TicketStatus.NEW
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
        created_at=NOW,
    )
    await db.commit()
    return ticket.id


@pytest.mark.parametrize("param", ["", "?token=unknown-token"])
async def test_ws_closes_with_4401_without_or_unknown_token(
    client: AsyncClient, param: str
) -> None:
    async with _ws_http() as ws_http:
        assert await _closed_with(ws_http, f"{WS_PATH}{param}") == 4401


async def test_ws_closes_with_4401_for_expired_token(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    async with _ws_http() as ws_http:
        assert await _closed_with(ws_http, f"{WS_PATH}?token={base.expired_token}") == 4401


async def test_ws_closes_with_4403_for_client_token(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    async with _ws_http() as ws_http:
        assert await _closed_with(ws_http, f"{WS_PATH}?token={base.client_token}") == 4403


async def test_ws_closes_with_4403_for_blocked_staff(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    async with _ws_http() as ws_http:
        assert await _closed_with(ws_http, f"{WS_PATH}?token={base.blocked_token}") == 4403


async def test_ws_receives_message_and_ticket_after_staff_reply(
    client: AsyncClient,
    db: AsyncSession,
    base: SimpleNamespace,
    messenger: FakeMessenger,
) -> None:
    ticket_id = await _create_ticket(db, base)

    async with (
        _ws_http() as ws_http,
        aconnect_ws(f"{WS_PATH}?token={base.manager_token}", ws_http) as ws,
    ):
        response = await client.post(
            f"/api/v1/staff/tickets/{ticket_id}/messages",
            data={"text": "Мастер придёт завтра"},
            headers=_auth(base.manager_token),
        )
        assert response.status_code == 201

        created = await _receive_json(ws)
        updated = await _receive_json(ws)

    assert created["type"] == "message_created"
    assert created["message"]["ticket_id"] == ticket_id
    assert created["message"]["sender_type"] == "STAFF"
    assert created["message"]["text"] == "Мастер придёт завтра"
    assert updated["type"] == "ticket_updated"
    assert updated["ticket"]["id"] == ticket_id
    assert updated["ticket"]["status"] == "IN_PROGRESS"
    assert updated["ticket"]["assignee"]["id"] == base.manager.id


async def test_ws_receives_ticket_updated_after_mark_read(
    client: AsyncClient,
    db: AsyncSession,
    base: SimpleNamespace,
) -> None:
    ticket_id = await _create_ticket(db, base, status=TicketStatus.IN_PROGRESS)
    await MessageRepository(db).create(
        ticket_id, SenderType.CLIENT, author_id=base.client.id, text="Когда мастер?"
    )
    ticket = await TicketRepository(db).get_by_id(ticket_id)
    assert ticket is not None
    ticket.last_client_message_at = NOW
    await db.commit()

    async with (
        _ws_http() as ws_http,
        aconnect_ws(f"{WS_PATH}?token={base.manager_token}", ws_http) as ws,
    ):
        response = await client.post(
            f"/api/v1/staff/tickets/{ticket_id}/read", headers=_auth(base.manager_token)
        )
        assert response.status_code == 204

        event = await _receive_json(ws)

    assert event["type"] == "ticket_updated"
    assert event["ticket"]["id"] == ticket_id
    assert event["ticket"]["unread"] is False


async def test_two_connections_both_receive_event(
    client: AsyncClient,
    db: AsyncSession,
    base: SimpleNamespace,
    messenger: FakeMessenger,
) -> None:
    ticket_id = await _create_ticket(db, base)

    async with (
        _ws_http() as ws_http,
        aconnect_ws(f"{WS_PATH}?token={base.manager_token}", ws_http) as first,
        aconnect_ws(f"{WS_PATH}?token={base.manager_token}", ws_http) as second,
    ):
        response = await client.post(
            f"/api/v1/staff/tickets/{ticket_id}/messages",
            data={"text": "Всем привет"},
            headers=_auth(base.manager_token),
        )
        assert response.status_code == 201

        first_created = await _receive_json(first)
        first_updated = await _receive_json(first)
        second_created = await _receive_json(second)
        second_updated = await _receive_json(second)

    assert first_created["type"] == "message_created"
    assert first_updated["type"] == "ticket_updated"
    assert second_created["type"] == "message_created"
    assert second_updated["type"] == "ticket_updated"


async def test_closed_panel_is_removed_from_manager(
    client: AsyncClient,
    base: SimpleNamespace,
) -> None:
    assert ws_manager._connections == []

    async with _ws_http() as ws_http:
        async with aconnect_ws(f"{WS_PATH}?token={base.manager_token}", ws_http):
            await _wait_until(lambda: len(ws_manager._connections) == 1)

        await _wait_until(lambda: ws_manager._connections == [])
