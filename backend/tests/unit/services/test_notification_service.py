from contextlib import ExitStack
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from src.core.constants import (
    RESOLVED_NO_PREFIX,
    RESOLVED_YES_PREFIX,
    ButtonType,
    SenderType,
    TicketStatus,
    TicketType,
    UserRole,
)
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
    messages: MagicMock | None = None,
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
            "src.services.notification_service.MessageRepository",
            return_value=messages or MagicMock(),
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


@pytest.fixture
def status_env():
    with ExitStack() as stack:
        publish = stack.enter_context(
            patch(
                "src.services.notification_service.publish_message_created",
                new_callable=AsyncMock,
            )
        )

        def build(ticket: Ticket, *, max_message_id: str | None = "card-1") -> SimpleNamespace:
            db = AsyncMock()
            messenger = AsyncMock()
            messenger.send_message.return_value = "mid-status-1"
            message = MagicMock()
            message.id = 88
            messages = MagicMock()
            messages.create = AsyncMock(return_value=message)
            status_changes = MagicMock()
            status_changes.list_by_ticket = AsyncMock(return_value=[])
            service = _service(db, messenger, messages=messages, status_changes=status_changes)
            ticket.status_message_max_id = max_message_id
            return SimpleNamespace(
                db=db,
                messenger=messenger,
                messages=messages,
                message=message,
                status_changes=status_changes,
                publish=publish,
                service=service,
            )

        yield build


async def test_send_status_message_in_progress_request(status_env) -> None:
    ticket = _ticket(status=TicketStatus.IN_PROGRESS)
    env = status_env(ticket)

    await env.service.send_status_message(ticket, None)

    text = "🟢 Статус заявки №1042: В работе."
    env.messenger.send_message.assert_awaited_once_with(555, text, buttons=None)
    env.messages.create.assert_awaited_once_with(
        ticket.id, SenderType.SYSTEM, text=text, max_message_id="mid-status-1"
    )
    env.db.commit.assert_awaited_once()
    env.publish.assert_awaited_once_with(env.db, env.message.id)
    env.messenger.edit_message.assert_awaited_once()
    assert env.messenger.edit_message.await_args.args[0] == "card-1"
    assert "markdown" not in env.messenger.send_message.await_args.kwargs


async def test_send_status_message_waiting_client_request(status_env) -> None:
    ticket = _ticket(status=TicketStatus.WAITING_CLIENT)
    env = status_env(ticket)

    await env.service.send_status_message(ticket, None)

    env.messenger.send_message.assert_awaited_once_with(
        555,
        "🟡 Статус заявки №1042: Нужен ваш ответ. Напишите его в этот чат.",
        buttons=None,
    )


async def test_send_status_message_rejected_with_reason(status_env) -> None:
    ticket = _ticket(status=TicketStatus.REJECTED)
    env = status_env(ticket)

    await env.service.send_status_message(ticket, "Не наш профиль")

    env.messenger.send_message.assert_awaited_once_with(
        555,
        "🔴 Статус заявки №1042: Отклонена.\nПричина: Не наш профиль",
        buttons=None,
    )


async def test_send_status_message_closed_request_has_resolved_buttons(status_env) -> None:
    ticket = _ticket(status=TicketStatus.CLOSED)
    env = status_env(ticket)

    await env.service.send_status_message(ticket, None)

    buttons = [
        [
            Button("Да", ButtonType.CALLBACK, f"{RESOLVED_YES_PREFIX}{ticket.id}"),
            Button("Нет", ButtonType.CALLBACK, f"{RESOLVED_NO_PREFIX}{ticket.id}"),
        ]
    ]
    env.messenger.send_message.assert_awaited_once_with(
        555,
        "🟢 Статус заявки №1042: Закрыта.\nПроблема решена?",
        buttons=buttons,
    )


async def test_send_status_message_question_uses_question_wording(status_env) -> None:
    ticket = _ticket(
        id=1047,
        type=TicketType.QUESTION,
        category_id=None,
        building_id=None,
        apartment=None,
        status=TicketStatus.CLOSED,
    )
    env = status_env(ticket)

    await env.service.send_status_message(ticket, None)

    env.messenger.send_message.assert_awaited_once_with(
        555,
        "🟢 Статус вопроса №1047: Закрыта.\nВопрос решён?",
        buttons=[
            [
                Button("Да", ButtonType.CALLBACK, f"{RESOLVED_YES_PREFIX}1047"),
                Button("Нет", ButtonType.CALLBACK, f"{RESOLVED_NO_PREFIX}1047"),
            ]
        ],
    )


async def test_send_status_message_without_id_saves_none(status_env) -> None:
    ticket = _ticket(status=TicketStatus.IN_PROGRESS)
    env = status_env(ticket)
    env.messenger.send_message.return_value = None

    await env.service.send_status_message(ticket, None)

    assert env.messages.create.await_args.kwargs["max_message_id"] is None
    env.db.commit.assert_awaited_once()
    env.publish.assert_awaited_once_with(env.db, env.message.id)


async def test_send_status_message_send_failure_saves_nothing(status_env) -> None:
    ticket = _ticket(status=TicketStatus.IN_PROGRESS)
    env = status_env(ticket)
    env.messenger.send_message.side_effect = MessengerException()

    with pytest.raises(MessengerException):
        await env.service.send_status_message(ticket, None)

    env.messages.create.assert_not_awaited()
    env.db.commit.assert_not_awaited()
    env.publish.assert_not_awaited()
    env.messenger.edit_message.assert_awaited_once()


async def test_notify_staff_reopened_sends_text_and_button() -> None:
    ticket = _ticket()
    messenger = AsyncMock()
    tickets = MagicMock()
    tickets.get_by_id = AsyncMock(return_value=ticket)
    users = MagicMock()
    users.list_staff = AsyncMock(return_value=[_staff(10, 1000)])
    service = _service(AsyncMock(), messenger, tickets=tickets, users=users)

    await service.notify_staff_reopened(1042)

    expected = (
        "🔄 Заявка №1042 · Мария Иванова\n"
        "Клиент сообщил, что проблема не решена — обращение снова в работе."
    )
    messenger.send_message.assert_awaited_once_with(
        1000, expected, buttons=[[Button("Открыть", ButtonType.OPEN_APP, "ticket_1042")]]
    )


async def test_notify_staff_reopened_sends_to_eligible_assignee_only() -> None:
    ticket = _ticket()
    ticket.assignee = _staff(10, 1000)
    ticket.assignee.role = UserRole.MANAGER
    ticket.assignee.is_blocked = False
    messenger = AsyncMock()
    tickets = MagicMock()
    tickets.get_by_id = AsyncMock(return_value=ticket)
    users = MagicMock()
    users.list_staff = AsyncMock(return_value=[_staff(11, 1001)])
    service = _service(AsyncMock(), messenger, tickets=tickets, users=users)

    await service.notify_staff_reopened(1042)

    messenger.send_message.assert_awaited_once()
    assert messenger.send_message.await_args.args[0] == 1000
    users.list_staff.assert_not_awaited()


@pytest.mark.parametrize(
    ("role", "is_blocked"),
    [(UserRole.CLIENT, False), (UserRole.MANAGER, True)],
)
async def test_notify_staff_reopened_ignores_ineligible_assignee(
    role: UserRole, is_blocked: bool
) -> None:
    ticket = _ticket()
    ticket.assignee = _staff(10, 1000)
    ticket.assignee.role = role
    ticket.assignee.is_blocked = is_blocked
    messenger = AsyncMock()
    tickets = MagicMock()
    tickets.get_by_id = AsyncMock(return_value=ticket)
    users = MagicMock()
    users.list_staff = AsyncMock(return_value=[_staff(11, 1001)])
    service = _service(AsyncMock(), messenger, tickets=tickets, users=users)

    await service.notify_staff_reopened(1042)

    users.list_staff.assert_awaited_once()
    messenger.send_message.assert_awaited_once()
    assert messenger.send_message.await_args.args[0] == 1001


async def test_notify_staff_reopened_survives_one_failing_recipient() -> None:
    ticket = _ticket()
    messenger = AsyncMock()
    messenger.send_message.side_effect = [MessengerException(), None]
    tickets = MagicMock()
    tickets.get_by_id = AsyncMock(return_value=ticket)
    users = MagicMock()
    users.list_staff = AsyncMock(return_value=[_staff(10, 1000), _staff(11, 1001)])
    service = _service(AsyncMock(), messenger, tickets=tickets, users=users)

    await service.notify_staff_reopened(1042)

    assert messenger.send_message.await_count == 2
    assert messenger.send_message.await_args_list[1].args[0] == 1001


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


def _message(*, text: str | None = "Здравствуйте, когда мастер?", files: int = 0) -> MagicMock:
    message = MagicMock()
    message.id = 77
    message.ticket_id = 1042
    message.text = text
    message.files = [MagicMock() for _ in range(files)]
    return message


async def test_update_status_card_edits_with_markdown() -> None:
    ticket = _ticket(status=TicketStatus.IN_PROGRESS)
    ticket.status_message_max_id = "mid-42"
    messenger = AsyncMock()
    status_changes = MagicMock()
    status_changes.list_by_ticket = AsyncMock(
        return_value=[
            StatusChange(
                ticket_id=1042,
                from_status=TicketStatus.NEW,
                to_status=TicketStatus.IN_PROGRESS,
                created_at=datetime(2026, 9, 25, 9, 30, tzinfo=UTC),
            )
        ]
    )
    service = _service(AsyncMock(), messenger, status_changes=status_changes)

    await service.update_status_card(ticket)

    expected = (
        "**Заявка №1042** · Сантехника\n"
        "ул. Ленина, 12, кв. 45\n"
        "\n"
        "🟢 В работе — 25.09 12:30\n"
        "⚪ Закрыта"
    )
    messenger.edit_message.assert_awaited_once_with("mid-42", expected, markdown=True)


async def test_update_status_card_without_message_id_does_nothing() -> None:
    ticket = _ticket()
    ticket.status_message_max_id = None
    messenger = AsyncMock()
    status_changes = MagicMock()
    status_changes.list_by_ticket = AsyncMock()
    service = _service(AsyncMock(), messenger, status_changes=status_changes)

    await service.update_status_card(ticket)

    messenger.edit_message.assert_not_awaited()
    status_changes.list_by_ticket.assert_not_awaited()


async def test_notify_staff_client_message_sends_to_assignee_only() -> None:
    ticket = _ticket()
    ticket.assignee = _staff(10, 1000)
    ticket.assignee.role = UserRole.MANAGER
    ticket.assignee.is_blocked = False
    messages = MagicMock()
    messages.get_by_id = AsyncMock(return_value=_message(files=2))
    tickets = MagicMock()
    tickets.get_by_id = AsyncMock(return_value=ticket)
    users = MagicMock()
    users.list_staff = AsyncMock(return_value=[_staff(11, 1001)])
    messenger = AsyncMock()
    service = _service(AsyncMock(), messenger, tickets=tickets, messages=messages, users=users)

    await service.notify_staff_client_message(77)

    expected = "💬 Заявка №1042 · Мария Иванова\n📎 Фото: 2\n\nЗдравствуйте, когда мастер?"
    messenger.send_message.assert_awaited_once_with(
        1000,
        expected,
        buttons=[[Button("Открыть", ButtonType.OPEN_APP, "ticket_1042")]],
    )
    users.list_staff.assert_not_awaited()


async def test_notify_staff_client_message_without_assignee_falls_back_to_all_staff() -> None:
    ticket = _ticket()
    messages = MagicMock()
    messages.get_by_id = AsyncMock(return_value=_message())
    tickets = MagicMock()
    tickets.get_by_id = AsyncMock(return_value=ticket)
    users = MagicMock()
    users.list_staff = AsyncMock(return_value=[_staff(10, 1000), _staff(11, 1001)])
    messenger = AsyncMock()
    service = _service(AsyncMock(), messenger, tickets=tickets, messages=messages, users=users)

    await service.notify_staff_client_message(77)

    assert messenger.send_message.await_count == 2


@pytest.mark.parametrize(
    ("role", "is_blocked"),
    [(UserRole.CLIENT, False), (UserRole.MANAGER, True)],
)
async def test_notify_staff_client_message_ignores_ineligible_assignee(
    role: UserRole, is_blocked: bool
) -> None:
    ticket = _ticket()
    ticket.assignee = _staff(10, 1000)
    ticket.assignee.role = role
    ticket.assignee.is_blocked = is_blocked
    messages = MagicMock()
    messages.get_by_id = AsyncMock(return_value=_message())
    tickets = MagicMock()
    tickets.get_by_id = AsyncMock(return_value=ticket)
    users = MagicMock()
    users.list_staff = AsyncMock(return_value=[_staff(11, 1001)])
    messenger = AsyncMock()
    service = _service(AsyncMock(), messenger, tickets=tickets, messages=messages, users=users)

    await service.notify_staff_client_message(77)

    users.list_staff.assert_awaited_once()
    messenger.send_message.assert_awaited_once()
    assert messenger.send_message.await_args.args[0] == 1001


async def test_notify_staff_client_message_survives_one_failing_recipient() -> None:
    ticket = _ticket()
    messages = MagicMock()
    messages.get_by_id = AsyncMock(return_value=_message())
    tickets = MagicMock()
    tickets.get_by_id = AsyncMock(return_value=ticket)
    users = MagicMock()
    users.list_staff = AsyncMock(return_value=[_staff(10, 1000), _staff(11, 1001)])
    messenger = AsyncMock()
    messenger.send_message.side_effect = [MessengerException(), None]
    service = _service(AsyncMock(), messenger, tickets=tickets, messages=messages, users=users)

    await service.notify_staff_client_message(77)

    assert messenger.send_message.await_count == 2
    assert messenger.send_message.await_args_list[1].args[0] == 1001


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
