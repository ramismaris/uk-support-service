from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.constants import ButtonType, SenderType, TicketStatus, TicketType, UserRole
from src.models.ticket import Ticket
from src.providers.messenger_provider import Button
from src.repositories.building_repository import BuildingRepository
from src.repositories.category_repository import CategoryRepository
from src.repositories.message_repository import MessageRepository
from src.repositories.status_change_repository import StatusChangeRepository
from src.repositories.ticket_repository import TicketRepository
from src.repositories.user_repository import UserRepository
from src.services.status_service import StatusService


class _FakeMessenger:
    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.edited: list[tuple[str, str]] = []

    async def send_message(
        self,
        user_id: int,
        text: str,
        *,
        buttons=None,
        files=None,
        markdown: bool = False,
    ) -> str:
        self.sent.append({"user_id": user_id, "text": text, "buttons": buttons})
        return f"mid-{len(self.sent)}"

    async def edit_message(
        self, message_id: str, text: str, *, buttons=None, markdown: bool = False
    ) -> None:
        self.edited.append((message_id, text))

    async def upload_file(self, data: bytes, mime: str, filename: str | None = None) -> None:
        return None

    async def download_file(self, url: str, max_size: int) -> tuple[bytes, str]:
        raise NotImplementedError

    async def close(self) -> None:
        return None


@contextmanager
def _background():
    with (
        patch("src.services.status_service.run_in_background") as run_bg,
        patch(
            "src.services.status_service.notify_staff_about_reopened_ticket",
            new=MagicMock(return_value="notify-coroutine"),
        ) as notify,
        patch(
            "src.services.status_service.publish_ticket_updated",
            new_callable=AsyncMock,
        ) as publish_ticket,
        patch(
            "src.services.notification_service.publish_message_created",
            new_callable=AsyncMock,
        ) as publish_message,
    ):
        yield SimpleNamespace(
            run_bg=run_bg,
            notify=notify,
            publish_ticket=publish_ticket,
            publish_message=publish_message,
        )


async def _make_request(
    db: AsyncSession,
    *,
    status: TicketStatus,
    client_id: int,
    assignee_id: int | None = None,
) -> Ticket:
    building = await BuildingRepository(db).create("ул. Ленина, 12")
    category = await CategoryRepository(db).create("Сантехника", 1)
    return await TicketRepository(db).create(
        type=TicketType.REQUEST,
        status=status,
        client_id=client_id,
        description="Течёт кран на кухне",
        assignee_id=assignee_id,
        category_id=category.id,
        building_id=building.id,
        apartment="45",
    )


async def test_full_status_flow_end_to_end(db: AsyncSession) -> None:
    users = UserRepository(db)
    client = await users.create(max_user_id=1000010, first_name="Мария", last_name="Иванова")
    manager = await users.create(max_user_id=1000011, first_name="Иван", role=UserRole.MANAGER)
    ticket = await _make_request(db, status=TicketStatus.NEW, client_id=client.id)
    await db.commit()

    messenger = _FakeMessenger()
    service = StatusService(db, messenger)

    with _background() as bg:
        taken = await service.change_by_staff(ticket.id, manager, TicketStatus.IN_PROGRESS, None)
        assert taken.status == TicketStatus.IN_PROGRESS
        assert taken.assignee_id == manager.id
        assert taken.closed_at is None

        waiting = await service.change_by_staff(
            ticket.id, manager, TicketStatus.WAITING_CLIENT, None
        )
        assert waiting.status == TicketStatus.WAITING_CLIENT

        closed = await service.change_by_staff(ticket.id, manager, TicketStatus.CLOSED, None)
        assert closed.status == TicketStatus.CLOSED
        assert closed.closed_at is not None

        reopened = await service.reopen_by_client(client, ticket.id)
        assert reopened.status == TicketStatus.IN_PROGRESS
        assert reopened.closed_at is None
        assert reopened.assignee_id == manager.id
        bg.run_bg.assert_called_once_with(
            bg.notify.return_value, name=f"notify-reopened-{ticket.id}"
        )
        bg.notify.assert_called_once_with(ticket.id)

        closed_again = await service.change_by_staff(ticket.id, manager, TicketStatus.CLOSED, None)
        assert closed_again.closed_at is not None

        rated = await service.rate(client, ticket.id, 5)
        assert rated.rating == 5
        overwritten = await service.rate(client, ticket.id, 4)
        assert overwritten.rating == 4

        assert bg.publish_ticket.await_count == 7
        assert bg.publish_message.await_count == 4

    stored = await TicketRepository(db).get_by_id(ticket.id)
    assert stored is not None
    assert stored.status == TicketStatus.CLOSED
    assert stored.rating == 4

    history = await StatusChangeRepository(db).list_by_ticket(ticket.id)
    assert [(change.from_status, change.to_status, change.changed_by_id) for change in history] == [
        (TicketStatus.NEW, TicketStatus.IN_PROGRESS, manager.id),
        (TicketStatus.IN_PROGRESS, TicketStatus.WAITING_CLIENT, manager.id),
        (TicketStatus.WAITING_CLIENT, TicketStatus.CLOSED, manager.id),
        (TicketStatus.CLOSED, TicketStatus.IN_PROGRESS, client.id),
        (TicketStatus.IN_PROGRESS, TicketStatus.CLOSED, manager.id),
    ]

    messages = await MessageRepository(db).list_by_ticket(ticket.id)
    system = [message for message in messages if message.sender_type == SenderType.SYSTEM]
    closed_text = f"🟢 Статус заявки №{ticket.id}: Закрыта.\nПроблема решена?"
    assert [(message.text, message.max_message_id, message.author_id) for message in system] == [
        (f"🟢 Статус заявки №{ticket.id}: В работе.", "mid-1", None),
        (
            f"🟡 Статус заявки №{ticket.id}: Нужен ваш ответ. Напишите его в этот чат.",
            "mid-2",
            None,
        ),
        (closed_text, "mid-3", None),
        (closed_text, "mid-4", None),
    ]

    assert messenger.sent[0]["buttons"] is None
    assert messenger.sent[2]["buttons"] == [
        [
            Button("Да", ButtonType.CALLBACK, f"resolved:yes:{ticket.id}"),
            Button("Нет", ButtonType.CALLBACK, f"resolved:no:{ticket.id}"),
        ]
    ]


async def test_reject_with_reason_then_admin_reopen(db: AsyncSession) -> None:
    users = UserRepository(db)
    client = await users.create(max_user_id=1000020, first_name="Мария")
    manager = await users.create(max_user_id=1000021, first_name="Иван", role=UserRole.MANAGER)
    admin = await users.create(max_user_id=1000022, first_name="Анна", role=UserRole.ADMIN)
    ticket = await _make_request(
        db, status=TicketStatus.IN_PROGRESS, client_id=client.id, assignee_id=manager.id
    )
    await db.commit()

    messenger = _FakeMessenger()
    service = StatusService(db, messenger)

    with _background():
        rejected = await service.change_by_staff(
            ticket.id, manager, TicketStatus.REJECTED, "Не наш профиль"
        )
        assert rejected.status == TicketStatus.REJECTED
        assert rejected.closed_at is not None
        assert rejected.assignee_id == manager.id

        reopened = await service.change_by_staff(ticket.id, admin, TicketStatus.IN_PROGRESS, None)
        assert reopened.status == TicketStatus.IN_PROGRESS
        assert reopened.closed_at is None
        assert reopened.assignee_id == manager.id

    history = await StatusChangeRepository(db).list_by_ticket(ticket.id)
    assert [(change.from_status, change.to_status, change.comment) for change in history] == [
        (TicketStatus.IN_PROGRESS, TicketStatus.REJECTED, "Не наш профиль"),
        (TicketStatus.REJECTED, TicketStatus.IN_PROGRESS, None),
    ]

    messages = await MessageRepository(db).list_by_ticket(ticket.id)
    assert messages[0].text == (
        f"🔴 Статус заявки №{ticket.id}: Отклонена.\nПричина: Не наш профиль"
    )


async def test_change_by_staff_uses_fresh_status(
    db: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    users = UserRepository(db)
    client = await users.create(max_user_id=1000030, first_name="Мария")
    manager = await users.create(max_user_id=1000031, first_name="Иван", role=UserRole.MANAGER)
    ticket = await _make_request(db, status=TicketStatus.NEW, client_id=client.id)
    await db.commit()

    loaded = await TicketRepository(db).get_by_id(ticket.id)
    assert loaded is not None
    assert loaded.status == TicketStatus.NEW

    async with session_factory() as other:
        other_ticket = await TicketRepository(other).get_by_id(ticket.id)
        assert other_ticket is not None
        other_ticket.status = TicketStatus.IN_PROGRESS
        await other.commit()

    service = StatusService(db, _FakeMessenger())

    with _background():
        result = await service.change_by_staff(
            ticket.id, manager, TicketStatus.WAITING_CLIENT, None
        )

    assert result.status == TicketStatus.WAITING_CLIENT
    history = await StatusChangeRepository(db).list_by_ticket(ticket.id)
    assert history[-1].from_status == TicketStatus.IN_PROGRESS
    assert history[-1].to_status == TicketStatus.WAITING_CLIENT
