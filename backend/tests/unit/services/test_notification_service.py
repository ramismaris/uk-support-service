from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, call, patch

from src.core.constants import ButtonType, TicketStatus, TicketType
from src.core.exceptions import MessengerException
from src.models.building import Building
from src.models.category import Category
from src.models.status_change import StatusChange
from src.models.ticket import Ticket
from src.models.user import User
from src.providers.messenger_provider import Button
from src.providers.noop_messenger_provider import NoopMessengerProvider
from src.services.notification_service import NotificationService

BUTTON = Button("Открыть", ButtonType.OPEN_APP, "ticket_1042")


def _ticket(**overrides) -> Ticket:
    values = {
        "id": 1042,
        "type": TicketType.REQUEST,
        "status": TicketStatus.NEW,
        "client_id": 1,
        "description": "Течёт кран на кухне, под раковиной лужа.",
        "category_id": 1,
        "building_id": 1,
        "apartment": "45",
        "contact_phone": "+7 (900) 000-00-03",
    }
    values.update(overrides)
    ticket = Ticket(**values)
    ticket.client = User(
        id=1, max_user_id=555, first_name="Мария", last_name="Иванова", phone="+7 (900) 111-11-11"
    )
    if ticket.type == TicketType.REQUEST:
        ticket.category = Category(id=1, title="Сантехника", sort_order=1)
        ticket.building = Building(id=1, address="ул. Ленина, 12")
    return ticket


def _service(
    db,
    messenger,
    *,
    tickets: MagicMock | None = None,
    files: MagicMock | None = None,
    status_changes: MagicMock | None = None,
    users: MagicMock | None = None,
) -> NotificationService:
    with (
        patch(
            "src.services.notification_service.TicketRepository",
            return_value=tickets or MagicMock(),
        ),
        patch(
            "src.services.notification_service.FileRepository",
            return_value=files or MagicMock(),
        ),
        patch(
            "src.services.notification_service.StatusChangeRepository",
            return_value=status_changes or MagicMock(),
        ),
        patch(
            "src.services.notification_service.UserRepository",
            return_value=users or MagicMock(),
        ),
    ):
        return NotificationService(db, messenger)


def _staff(id_: int, max_user_id: int) -> MagicMock:
    staff = MagicMock()
    staff.id = id_
    staff.max_user_id = max_user_id
    return staff


async def test_send_status_card_sends_markdown_and_stores_message_id() -> None:
    ticket = _ticket()
    db = AsyncMock()
    messenger = AsyncMock()
    messenger.send_message.return_value = "mid-42"
    status_changes = MagicMock()
    status_changes.list_by_ticket = AsyncMock(
        return_value=[
            StatusChange(
                ticket_id=1042,
                from_status=None,
                to_status=TicketStatus.NEW,
                created_at=datetime(2026, 9, 25, 9, 4, tzinfo=UTC),
            )
        ]
    )
    service = _service(db, messenger, status_changes=status_changes)

    await service.send_status_card(ticket)

    expected = (
        "**Заявка №1042** · Сантехника\n"
        "ул. Ленина, 12, кв. 45\n"
        "\n"
        "🟢 Принята — 25.09 12:04\n"
        "⚪ В работе\n"
        "⚪ Закрыта"
    )
    messenger.send_message.assert_awaited_once_with(555, expected, markdown=True)
    assert ticket.status_message_max_id == "mid-42"
    db.commit.assert_awaited_once()


async def test_send_status_card_with_noop_messenger_stores_nothing() -> None:
    ticket = _ticket()
    db = AsyncMock()
    status_changes = MagicMock()
    status_changes.list_by_ticket = AsyncMock(return_value=[])
    service = _service(db, NoopMessengerProvider(), status_changes=status_changes)

    await service.send_status_card(ticket)

    assert ticket.status_message_max_id is None
    db.commit.assert_not_awaited()


async def test_notify_staff_new_ticket_sends_exact_text_and_button() -> None:
    ticket = _ticket()
    db = AsyncMock()
    messenger = AsyncMock()
    tickets = MagicMock()
    tickets.get_by_id = AsyncMock(return_value=ticket)
    files = MagicMock()
    files.list_by_ticket = AsyncMock(return_value=[MagicMock(), MagicMock()])
    users = MagicMock()
    users.list_staff = AsyncMock(return_value=[_staff(10, 1000), _staff(11, 1001)])
    service = _service(db, messenger, tickets=tickets, files=files, users=users)

    await service.notify_staff_new_ticket(1042)

    expected = (
        "🆕 Заявка №1042 · Сантехника\n"
        "ул. Ленина, 12, кв. 45\n"
        "Мария Иванова, +7 (900) 000-00-03\n"
        "📎 Фото: 2\n"
        "\n"
        "Течёт кран на кухне, под раковиной лужа."
    )
    assert messenger.send_message.await_args_list == [
        call(1000, expected, buttons=[[BUTTON]]),
        call(1001, expected, buttons=[[BUTTON]]),
    ]


async def test_notify_staff_survives_one_failing_recipient() -> None:
    ticket = _ticket()
    messenger = AsyncMock()
    messenger.send_message.side_effect = [MessengerException(), None]
    tickets = MagicMock()
    tickets.get_by_id = AsyncMock(return_value=ticket)
    files = MagicMock()
    files.list_by_ticket = AsyncMock(return_value=[])
    users = MagicMock()
    users.list_staff = AsyncMock(return_value=[_staff(10, 1000), _staff(11, 1001)])
    service = _service(
        messenger=messenger, db=AsyncMock(), tickets=tickets, files=files, users=users
    )

    await service.notify_staff_new_ticket(1042)

    assert messenger.send_message.await_count == 2
    assert messenger.send_message.await_args_list[1].args[0] == 1001


async def test_notify_staff_cuts_long_description_to_500_characters() -> None:
    ticket = _ticket(description="а" * 600)
    messenger = AsyncMock()
    tickets = MagicMock()
    tickets.get_by_id = AsyncMock(return_value=ticket)
    files = MagicMock()
    files.list_by_ticket = AsyncMock(return_value=[])
    users = MagicMock()
    users.list_staff = AsyncMock(return_value=[_staff(10, 1000)])
    service = _service(
        messenger=messenger, db=AsyncMock(), tickets=tickets, files=files, users=users
    )

    await service.notify_staff_new_ticket(1042)

    text = messenger.send_message.await_args.args[1]
    assert text.endswith("а" * 500 + "…")
    assert "а" * 501 not in text


async def test_notify_staff_omits_photo_line_without_photos() -> None:
    ticket = _ticket()
    messenger = AsyncMock()
    tickets = MagicMock()
    tickets.get_by_id = AsyncMock(return_value=ticket)
    files = MagicMock()
    files.list_by_ticket = AsyncMock(return_value=[])
    users = MagicMock()
    users.list_staff = AsyncMock(return_value=[_staff(10, 1000)])
    service = _service(
        messenger=messenger, db=AsyncMock(), tickets=tickets, files=files, users=users
    )

    await service.notify_staff_new_ticket(1042)

    text = messenger.send_message.await_args.args[1]
    assert "📎" not in text


async def test_notify_staff_question_has_no_category_or_address() -> None:
    ticket = _ticket(
        id=1047,
        type=TicketType.QUESTION,
        category_id=None,
        building_id=None,
        apartment=None,
    )
    messenger = AsyncMock()
    tickets = MagicMock()
    tickets.get_by_id = AsyncMock(return_value=ticket)
    files = MagicMock()
    files.list_by_ticket = AsyncMock(return_value=[])
    users = MagicMock()
    users.list_staff = AsyncMock(return_value=[_staff(10, 1000)])
    service = _service(
        messenger=messenger, db=AsyncMock(), tickets=tickets, files=files, users=users
    )

    await service.notify_staff_new_ticket(1047)

    text = messenger.send_message.await_args.args[1]
    assert text == (
        "🆕 Вопрос №1047\n"
        "Мария Иванова, +7 (900) 000-00-03\n"
        "\n"
        "Течёт кран на кухне, под раковиной лужа."
    )
    assert "ул. Ленина" not in text
    assert "Сантехника" not in text
