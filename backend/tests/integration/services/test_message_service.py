from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.constants import SenderType, TicketStatus, TicketType, UserRole
from src.core.exceptions import ConflictException
from src.providers.local_storage_provider import LocalStorageProvider
from src.repositories.file_repository import FileRepository
from src.repositories.message_repository import MessageRepository
from src.repositories.status_change_repository import StatusChangeRepository
from src.repositories.ticket_repository import TicketRepository
from src.repositories.user_repository import UserRepository
from src.services.message_service import MessageService, UploadedFile
from src.services.ticket_rules import ToTicket


async def _make_ticket(db: AsyncSession, *, status: TicketStatus, client_id: int):
    return await TicketRepository(db).create(
        type=TicketType.QUESTION,
        status=status,
        client_id=client_id,
        description="Вопрос по дому",
    )


async def test_send_staff_message_end_to_end(db: AsyncSession, tmp_path) -> None:
    users = UserRepository(db)
    client = await users.create(max_user_id=1000003, first_name="Мария")
    author = await users.create(max_user_id=1000004, first_name="Иван", role=UserRole.MANAGER)
    ticket = await _make_ticket(db, status=TicketStatus.NEW, client_id=client.id)
    await db.commit()

    messenger = AsyncMock()
    messenger.send_message.return_value = "mid-staff-1"
    messenger.upload_file.return_value = "tok-1"
    service = MessageService(db, messenger, LocalStorageProvider(str(tmp_path)))

    message = await service.send_staff_message(
        ticket.id,
        author,
        "Мастер придёт завтра",
        [UploadedFile(data=b"img", mime="image/webp", filename="a.webp")],
    )

    assert message.sender_type == SenderType.STAFF
    assert message.author is not None
    assert message.author.id == author.id
    assert message.text == "Мастер придёт завтра"
    assert message.max_message_id == "mid-staff-1"

    assert len(message.files) == 1
    assert message.files[0].ticket_id == ticket.id
    assert message.files[0].message_id == message.id
    assert message.files[0].max_token == "tok-1"

    stored = await TicketRepository(db).get_by_id(ticket.id)
    assert stored is not None
    assert stored.status == TicketStatus.IN_PROGRESS
    assert stored.assignee_id == author.id

    history = await StatusChangeRepository(db).list_by_ticket(ticket.id)
    assert len(history) == 1
    assert history[0].from_status == TicketStatus.NEW
    assert history[0].to_status == TicketStatus.IN_PROGRESS
    assert history[0].changed_by_id is None

    messenger.upload_file.assert_awaited_once_with(b"img", "image/webp", "a.webp")
    messenger.send_message.assert_awaited_once()


async def test_add_client_message_end_to_end(db: AsyncSession, tmp_path) -> None:
    users = UserRepository(db)
    client = await users.create(max_user_id=1000005, first_name="Мария")
    ticket = await _make_ticket(db, status=TicketStatus.WAITING_CLIENT, client_id=client.id)
    photo = await FileRepository(db).create(storage_key="files/x.webp", mime="image/webp", size=3)
    await db.commit()

    service = MessageService(db, AsyncMock(), LocalStorageProvider(str(tmp_path)))

    with (
        patch("src.services.message_service.run_in_background") as run_bg,
        patch(
            "src.services.message_service.notify_staff_about_client_message",
            new=MagicMock(return_value="notify-coroutine"),
        ) as notify,
    ):
        message = await service.add_client_message(
            client,
            ticket.id,
            text="Уже сделали?",
            file_ids=[photo.id],
            max_message_id="mid-in",
        )

    assert message.sender_type == SenderType.CLIENT
    assert message.author_id == client.id
    assert message.max_message_id == "mid-in"

    stored_photo = await FileRepository(db).get_by_id(photo.id)
    assert stored_photo is not None
    assert stored_photo.ticket_id == ticket.id
    assert stored_photo.message_id == message.id

    stored = await TicketRepository(db).get_by_id(ticket.id)
    assert stored is not None
    assert stored.status == TicketStatus.IN_PROGRESS
    assert stored.last_client_message_at is not None

    user = await UserRepository(db).get_by_id(client.id)
    assert user is not None
    assert user.active_ticket_id == ticket.id

    history = await StatusChangeRepository(db).list_by_ticket(ticket.id)
    assert len(history) == 1
    assert history[0].from_status == TicketStatus.WAITING_CLIENT
    assert history[0].to_status == TicketStatus.IN_PROGRESS
    assert history[0].changed_by_id is None

    run_bg.assert_called_once_with(notify.return_value, name=f"notify-client-message-{message.id}")
    notify.assert_called_once_with(message.id)


async def test_add_client_message_sees_ticket_closed_elsewhere(
    db: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path,
) -> None:
    users = UserRepository(db)
    client = await users.create(max_user_id=1000006, first_name="Мария")
    ticket = await _make_ticket(db, status=TicketStatus.NEW, client_id=client.id)
    await db.commit()

    loaded = await TicketRepository(db).get_by_id(ticket.id)
    assert loaded is not None
    assert loaded.status == TicketStatus.NEW

    async with session_factory() as other:
        other_ticket = await TicketRepository(other).get_by_id(ticket.id)
        assert other_ticket is not None
        other_ticket.status = TicketStatus.CLOSED
        await other.commit()

    service = MessageService(db, AsyncMock(), LocalStorageProvider(str(tmp_path)))

    with pytest.raises(ConflictException) as exc:
        await service.add_client_message(
            client, ticket.id, text="Привет", file_ids=[], max_message_id=None
        )

    assert exc.value.status_code == 409
    assert loaded.status == TicketStatus.CLOSED


async def test_resolve_client_route_reply_to_staff_message(db: AsyncSession, tmp_path) -> None:
    users = UserRepository(db)
    client = await users.create(max_user_id=1000007, first_name="Мария")
    ticket = await _make_ticket(db, status=TicketStatus.IN_PROGRESS, client_id=client.id)
    await MessageRepository(db).create(
        ticket.id,
        SenderType.STAFF,
        author_id=None,
        text="Ответ",
        max_message_id="mid-staff",
    )
    await db.commit()

    service = MessageService(db, AsyncMock(), LocalStorageProvider(str(tmp_path)))

    result = await service.resolve_client_route(client, "mid-staff")

    assert result == ToTicket(ticket_id=ticket.id)
