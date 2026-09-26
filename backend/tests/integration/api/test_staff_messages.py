from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import SenderType, TicketStatus, TicketType, UserRole
from src.core.exceptions import MessengerException
from src.core.security import hash_token
from src.core.texts import MESSAGE_FILES_MIXED, TEXT_INVALID_CHARACTER
from src.main import app
from src.models.message import Message
from src.models.ticket import Ticket
from src.providers.factory import get_messenger_provider, get_storage_provider
from src.providers.local_storage_provider import LocalStorageProvider
from src.repositories.auth_token_repository import AuthTokenRepository
from src.repositories.building_repository import BuildingRepository
from src.repositories.category_repository import CategoryRepository
from src.repositories.message_repository import MessageRepository
from src.repositories.ticket_repository import TicketRepository
from src.repositories.user_repository import UserRepository
from src.services.file_service import FileService

NOW = datetime(2026, 9, 25, 12, 0, tzinfo=UTC)


class FakeMessenger:
    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.uploads: list[tuple[bytes, str, str | None]] = []
        self.fail_send = False
        self.fail_upload = False

    async def send_message(self, user_id, text, *, buttons=None, files=None, markdown=False):
        if self.fail_send:
            raise MessengerException()
        self.sent.append({"user_id": user_id, "text": text, "buttons": buttons, "files": files})
        return f"mid-{len(self.sent)}"

    async def edit_message(self, message_id, text, *, buttons=None, markdown=False) -> None:
        return None

    async def upload_file(self, data, mime, filename=None):
        if self.fail_upload:
            raise MessengerException()
        self.uploads.append((data, mime, filename))
        return f"tok-{len(self.uploads)}"

    async def download_file(self, url, max_size):
        raise MessengerException()

    async def close(self) -> None:
        return None


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


async def _issue_token(db: AsyncSession, user) -> str:
    token = f"staff-messages-token-{user.id}"
    await AuthTokenRepository(db).create(
        user.id, hash_token(token), datetime.now(UTC) + timedelta(days=1)
    )
    return token


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def base(db: AsyncSession) -> SimpleNamespace:
    users = UserRepository(db)
    client = await users.create(max_user_id=2000003, first_name="Мария", phone="+7 (900) 111-11-11")
    manager = await users.create(max_user_id=2000002, first_name="Игорь", role=UserRole.MANAGER)
    admin = await users.create(max_user_id=2000001, first_name="Анна", role=UserRole.ADMIN)

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
    created_at: datetime = NOW,
    assignee=None,
    description: str = "Описание обращения",
) -> int:
    ticket = await TicketRepository(db).create(
        type=TicketType.REQUEST,
        status=status,
        client_id=base.client.id,
        description=description,
        category_id=base.category.id,
        building_id=base.building.id,
        apartment="45",
        contact_phone="+7 (900) 111-11-11",
        assignee_id=assignee.id if assignee else None,
        created_at=created_at,
    )
    await db.commit()
    return ticket.id


async def _set_last_client_message_at(
    db: AsyncSession,
    ticket_id: int,
    value: datetime | None,
    staff_seen_at: datetime | None = None,
) -> None:
    ticket = await db.get(Ticket, ticket_id)
    assert ticket is not None
    ticket.last_client_message_at = value
    ticket.staff_seen_at = staff_seen_at
    await db.commit()


async def _messages_count(db: AsyncSession, ticket_id: int) -> int:
    return await db.scalar(
        select(func.count()).select_from(Message).where(Message.ticket_id == ticket_id)
    )


async def test_list_messages_oldest_first_with_author_and_files(
    client: AsyncClient,
    db: AsyncSession,
    base: SimpleNamespace,
    storage: LocalStorageProvider,
) -> None:
    ticket_id = await _create_ticket(db, base, status=TicketStatus.IN_PROGRESS)
    messages = MessageRepository(db)
    first = await messages.create(
        ticket_id,
        SenderType.CLIENT,
        author_id=base.client.id,
        text="Когда придёт мастер?",
        created_at=NOW - timedelta(minutes=10),
    )
    await FileService(db, storage).save(
        b"client-photo",
        "image/webp",
        original_name="photo.webp",
        ticket_id=ticket_id,
        message_id=first.id,
    )
    second = await messages.create(
        ticket_id,
        SenderType.STAFF,
        author_id=base.manager.id,
        text="Сегодня после 18:00.",
        created_at=NOW - timedelta(minutes=5),
    )
    await db.commit()

    resp = await client.get(
        f"/api/v1/staff/tickets/{ticket_id}/messages", headers=_auth(base.manager_token)
    )

    assert resp.status_code == 200
    body = resp.json()
    assert [message["id"] for message in body] == [first.id, second.id]
    assert [message["sender_type"] for message in body] == ["CLIENT", "STAFF"]
    assert body[0]["author"]["id"] == base.client.id
    assert body[0]["text"] == "Когда придёт мастер?"
    assert body[1]["author"]["id"] == base.manager.id
    assert body[0]["created_at"] < body[1]["created_at"]
    assert body[1]["files"] == []

    assert len(body[0]["files"]) == 1
    file_url = body[0]["files"][0]["url"]
    download = await client.get(file_url)
    assert download.status_code == 200
    assert download.content == b"client-photo"


async def test_list_messages_unknown_ticket_returns_404(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    resp = await client.get(
        "/api/v1/staff/tickets/999999/messages", headers=_auth(base.manager_token)
    )

    assert resp.status_code == 404
    assert resp.json() == {"detail": "Обращение не найдено"}


async def test_list_messages_empty_chat(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    ticket_id = await _create_ticket(db, base)

    resp = await client.get(
        f"/api/v1/staff/tickets/{ticket_id}/messages", headers=_auth(base.manager_token)
    )

    assert resp.status_code == 200
    assert resp.json() == []


async def test_send_message_text_only(
    client: AsyncClient,
    db: AsyncSession,
    base: SimpleNamespace,
    messenger: FakeMessenger,
) -> None:
    ticket_id = await _create_ticket(db, base, status=TicketStatus.NEW)

    resp = await client.post(
        f"/api/v1/staff/tickets/{ticket_id}/messages",
        data={"text": "Мастер придёт завтра"},
        headers=_auth(base.manager_token),
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["ticket_id"] == ticket_id
    assert body["sender_type"] == "STAFF"
    assert body["author"]["id"] == base.manager.id
    assert body["text"] == "Мастер придёт завтра"
    assert body["files"] == []

    assert len(messenger.sent) == 1
    assert messenger.sent[0]["user_id"] == base.client.max_user_id
    assert "Заявка №" in messenger.sent[0]["text"]
    assert "Мастер придёт завтра" in messenger.sent[0]["text"]

    card = await client.get(f"/api/v1/staff/tickets/{ticket_id}", headers=_auth(base.manager_token))
    assert card.status_code == 200
    assert card.json()["status"] == "IN_PROGRESS"
    assert card.json()["assignee"]["id"] == base.manager.id


async def test_send_message_with_two_images(
    client: AsyncClient,
    db: AsyncSession,
    base: SimpleNamespace,
    messenger: FakeMessenger,
) -> None:
    ticket_id = await _create_ticket(db, base, status=TicketStatus.IN_PROGRESS)

    resp = await client.post(
        f"/api/v1/staff/tickets/{ticket_id}/messages",
        data={"text": "Фото"},
        files=[
            ("files", ("one.png", b"first-image", "image/png")),
            ("files", ("two.png", b"second-image", "image/png")),
        ],
        headers=_auth(base.manager_token),
    )

    assert resp.status_code == 201
    body = resp.json()
    assert len(body["files"]) == 2
    assert len(messenger.uploads) == 2

    for file, expected in zip(body["files"], (b"first-image", b"second-image"), strict=True):
        download = await client.get(file["url"])
        assert download.status_code == 200
        assert download.content == expected


async def test_send_message_with_single_document(
    client: AsyncClient,
    db: AsyncSession,
    base: SimpleNamespace,
    messenger: FakeMessenger,
) -> None:
    ticket_id = await _create_ticket(db, base, status=TicketStatus.IN_PROGRESS)

    resp = await client.post(
        f"/api/v1/staff/tickets/{ticket_id}/messages",
        files=[("files", ("act.pdf", b"%PDF-1.7", "application/pdf"))],
        headers=_auth(base.manager_token),
    )

    assert resp.status_code == 201
    body = resp.json()
    assert len(body["files"]) == 1
    assert body["files"][0]["mime"] == "application/pdf"
    assert messenger.uploads == [(b"%PDF-1.7", "application/pdf", "act.pdf")]


async def test_send_message_rejects_document_with_photo(
    client: AsyncClient,
    db: AsyncSession,
    base: SimpleNamespace,
    messenger: FakeMessenger,
) -> None:
    ticket_id = await _create_ticket(db, base, status=TicketStatus.IN_PROGRESS)

    resp = await client.post(
        f"/api/v1/staff/tickets/{ticket_id}/messages",
        files=[
            ("files", ("one.png", b"image", "image/png")),
            ("files", ("act.pdf", b"%PDF", "application/pdf")),
        ],
        headers=_auth(base.manager_token),
    )

    assert resp.status_code == 400
    assert resp.json() == {"detail": MESSAGE_FILES_MIXED}
    assert messenger.sent == []
    assert messenger.uploads == []
    assert await _messages_count(db, ticket_id) == 0


async def test_send_message_blank_without_files_returns_400(
    client: AsyncClient,
    db: AsyncSession,
    base: SimpleNamespace,
    messenger: FakeMessenger,
) -> None:
    ticket_id = await _create_ticket(db, base, status=TicketStatus.IN_PROGRESS)

    resp = await client.post(
        f"/api/v1/staff/tickets/{ticket_id}/messages",
        data={"text": "   "},
        headers=_auth(base.manager_token),
    )

    assert resp.status_code == 400
    assert messenger.sent == []
    assert await _messages_count(db, ticket_id) == 0


async def test_send_message_text_with_nul_returns_400_and_saves_nothing(
    client: AsyncClient,
    db: AsyncSession,
    base: SimpleNamespace,
    messenger: FakeMessenger,
) -> None:
    ticket_id = await _create_ticket(db, base, status=TicketStatus.IN_PROGRESS)

    resp = await client.post(
        f"/api/v1/staff/tickets/{ticket_id}/messages",
        data={"text": "a\x00b"},
        headers=_auth(base.manager_token),
    )

    assert resp.status_code == 400
    assert resp.json() == {"detail": TEXT_INVALID_CHARACTER}
    assert messenger.sent == []
    assert messenger.uploads == []
    assert await _messages_count(db, ticket_id) == 0


async def test_send_message_rejects_eleven_files(
    client: AsyncClient,
    db: AsyncSession,
    base: SimpleNamespace,
    messenger: FakeMessenger,
) -> None:
    ticket_id = await _create_ticket(db, base, status=TicketStatus.IN_PROGRESS)

    resp = await client.post(
        f"/api/v1/staff/tickets/{ticket_id}/messages",
        files=[("files", (f"photo-{index}.png", b"image", "image/png")) for index in range(11)],
        headers=_auth(base.manager_token),
    )

    assert resp.status_code == 400
    assert messenger.sent == []
    assert await _messages_count(db, ticket_id) == 0


async def test_send_message_file_over_limit_returns_413(
    client: AsyncClient,
    db: AsyncSession,
    base: SimpleNamespace,
    messenger: FakeMessenger,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("src.services.file_service.MAX_FILE_SIZE", 8)
    monkeypatch.setattr("src.api.v1.staff.router.MAX_FILE_SIZE", 8)
    ticket_id = await _create_ticket(db, base, status=TicketStatus.IN_PROGRESS)

    resp = await client.post(
        f"/api/v1/staff/tickets/{ticket_id}/messages",
        files=[("files", ("big.png", b"0123456789", "image/png"))],
        headers=_auth(base.manager_token),
    )

    assert resp.status_code == 413
    assert messenger.sent == []
    assert await _messages_count(db, ticket_id) == 0


async def test_send_message_to_closed_ticket_returns_409(
    client: AsyncClient,
    db: AsyncSession,
    base: SimpleNamespace,
    messenger: FakeMessenger,
) -> None:
    ticket_id = await _create_ticket(db, base, status=TicketStatus.CLOSED)

    resp = await client.post(
        f"/api/v1/staff/tickets/{ticket_id}/messages",
        data={"text": "Ещё вопрос"},
        headers=_auth(base.manager_token),
    )

    assert resp.status_code == 409
    assert messenger.sent == []
    assert await _messages_count(db, ticket_id) == 0


async def test_send_message_unknown_ticket_returns_404(
    client: AsyncClient, base: SimpleNamespace, messenger: FakeMessenger
) -> None:
    resp = await client.post(
        "/api/v1/staff/tickets/999999/messages",
        data={"text": "Текст"},
        headers=_auth(base.manager_token),
    )

    assert resp.status_code == 404
    assert resp.json() == {"detail": "Обращение не найдено"}
    assert messenger.sent == []


async def test_send_message_messenger_failure_returns_502_and_saves_nothing(
    client: AsyncClient,
    db: AsyncSession,
    base: SimpleNamespace,
    messenger: FakeMessenger,
) -> None:
    ticket_id = await _create_ticket(db, base, status=TicketStatus.NEW)
    messenger.fail_send = True

    resp = await client.post(
        f"/api/v1/staff/tickets/{ticket_id}/messages",
        data={"text": "Текст"},
        headers=_auth(base.manager_token),
    )

    assert resp.status_code == 502
    assert await _messages_count(db, ticket_id) == 0

    chat = await client.get(
        f"/api/v1/staff/tickets/{ticket_id}/messages", headers=_auth(base.manager_token)
    )
    assert chat.json() == []

    card = await client.get(f"/api/v1/staff/tickets/{ticket_id}", headers=_auth(base.manager_token))
    assert card.json()["status"] == "NEW"
    assert card.json()["assignee"] is None


async def test_send_message_upload_failure_returns_502_and_saves_nothing(
    client: AsyncClient,
    db: AsyncSession,
    base: SimpleNamespace,
    messenger: FakeMessenger,
) -> None:
    ticket_id = await _create_ticket(db, base, status=TicketStatus.IN_PROGRESS)
    messenger.fail_upload = True

    resp = await client.post(
        f"/api/v1/staff/tickets/{ticket_id}/messages",
        files=[("files", ("one.png", b"image", "image/png"))],
        headers=_auth(base.manager_token),
    )

    assert resp.status_code == 502
    assert messenger.sent == []
    assert await _messages_count(db, ticket_id) == 0


async def test_unread_flag_true_until_marked_read(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    ticket_id = await _create_ticket(db, base, status=TicketStatus.IN_PROGRESS)
    await _set_last_client_message_at(db, ticket_id, NOW)

    listing = await client.get("/api/v1/staff/tickets", headers=_auth(base.manager_token))
    item = next(item for item in listing.json()["items"] if item["id"] == ticket_id)
    assert item["unread"] is True
    assert item["last_client_message_at"].startswith("2026-09-25T12:00:00")
    assert "staff_seen_at" not in item

    card = await client.get(f"/api/v1/staff/tickets/{ticket_id}", headers=_auth(base.manager_token))
    assert card.json()["unread"] is True
    assert "staff_seen_at" not in card.json()

    read = await client.post(
        f"/api/v1/staff/tickets/{ticket_id}/read", headers=_auth(base.manager_token)
    )
    assert read.status_code == 204
    assert read.content == b""

    listing_after = await client.get("/api/v1/staff/tickets", headers=_auth(base.manager_token))
    item_after = next(item for item in listing_after.json()["items"] if item["id"] == ticket_id)
    assert item_after["unread"] is False

    card_after = await client.get(
        f"/api/v1/staff/tickets/{ticket_id}", headers=_auth(base.manager_token)
    )
    assert card_after.json()["unread"] is False


async def test_unread_stays_false_when_client_message_already_seen(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    ticket_id = await _create_ticket(db, base, status=TicketStatus.IN_PROGRESS)
    await _set_last_client_message_at(db, ticket_id, NOW - timedelta(minutes=5), staff_seen_at=NOW)

    card = await client.get(f"/api/v1/staff/tickets/{ticket_id}", headers=_auth(base.manager_token))

    assert card.json()["unread"] is False


async def test_mark_read_unknown_ticket_returns_404(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    resp = await client.post("/api/v1/staff/tickets/999999/read", headers=_auth(base.manager_token))

    assert resp.status_code == 404
    assert resp.json() == {"detail": "Обращение не найдено"}


CHAT_ROUTES = [
    pytest.param("GET", "messages", None, id="list"),
    pytest.param("POST", "messages", {"text": "Текст"}, id="send"),
    pytest.param("POST", "read", None, id="read"),
]


async def _chat_request(
    client: AsyncClient,
    method: str,
    suffix: str,
    ticket_id: int,
    *,
    headers: dict[str, str] | None = None,
    data: dict | None = None,
):
    url = f"/api/v1/staff/tickets/{ticket_id}/{suffix}"
    if method == "GET":
        return await client.get(url, headers=headers)
    return await client.post(url, data=data, headers=headers)


@pytest.mark.parametrize(("method", "suffix", "data"), CHAT_ROUTES)
async def test_chat_routes_require_token(
    client: AsyncClient, method: str, suffix: str, data: dict | None
) -> None:
    resp = await _chat_request(client, method, suffix, 1, data=data)

    assert resp.status_code == 401


@pytest.mark.parametrize(("method", "suffix", "data"), CHAT_ROUTES)
async def test_chat_routes_forbidden_for_client(
    client: AsyncClient,
    base: SimpleNamespace,
    method: str,
    suffix: str,
    data: dict | None,
) -> None:
    resp = await _chat_request(
        client, method, suffix, 1, headers=_auth(base.client_token), data=data
    )

    assert resp.status_code == 403


@pytest.mark.parametrize(("method", "suffix", "data"), CHAT_ROUTES)
@pytest.mark.parametrize("ticket_id", [0, 2**63])
async def test_chat_routes_reject_out_of_range_ticket_id(
    client: AsyncClient,
    base: SimpleNamespace,
    method: str,
    suffix: str,
    data: dict | None,
    ticket_id: int,
) -> None:
    resp = await _chat_request(
        client, method, suffix, ticket_id, headers=_auth(base.manager_token), data=data
    )

    assert resp.status_code == 422


@pytest.mark.parametrize(("method", "suffix", "data"), CHAT_ROUTES)
async def test_chat_routes_accept_max_bigint_ticket_id(
    client: AsyncClient,
    base: SimpleNamespace,
    method: str,
    suffix: str,
    data: dict | None,
) -> None:
    resp = await _chat_request(
        client, method, suffix, 2**63 - 1, headers=_auth(base.manager_token), data=data
    )

    assert resp.status_code == 404
