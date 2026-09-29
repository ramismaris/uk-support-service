from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from maxapi.context import MemoryContext
from maxapi.enums.parse_mode import ParseMode
from maxapi.enums.upload_type import UploadType
from maxapi.exceptions import MaxApiError
from maxapi.types import BotStarted, MessageCallback, MessageCreated
from maxapi.types.attachments.upload import AttachmentUpload

from src.bot.handlers import menu
from src.core.constants import MENU_START, TicketStatus, TicketType
from src.core.texts import (
    MAIN_MENU_BUTTON,
    MY_TICKETS_EMPTY,
    OUTDATED_BUTTON_TEXT,
    QUESTION_SECTION_DEFAULT,
    SECTION_EMPTY_TEXT,
    USE_MENU_TEXT,
)
from src.schemas.content import (
    ContactPhone,
    ContactsContent,
    EmergencyContent,
    PaymentContent,
    ServicesContent,
)
from src.services.welcome_service import WelcomeMessage


def _sent(mid: str = "mid-answer") -> SimpleNamespace:
    return SimpleNamespace(message=SimpleNamespace(body=SimpleNamespace(mid=mid)))


def _bot() -> MagicMock:
    bot = MagicMock()
    bot.edit_message = AsyncMock(return_value=SimpleNamespace(success=True))
    bot.send_message = AsyncMock()
    return bot


def _message_created() -> MagicMock:
    event = MagicMock(spec=MessageCreated)
    event.bot = _bot()
    message = MagicMock()
    message.answer = AsyncMock(return_value=_sent())
    message.body.mid = "mid-incoming"
    event.message = message
    return event


def _bot_started() -> MagicMock:
    event = MagicMock(spec=BotStarted)
    event.chat_id = 7
    event.bot = _bot()
    return event


def _message_callback(payload: str = "menu:emergency") -> MagicMock:
    event = MagicMock(spec=MessageCallback)
    event.edit = AsyncMock()
    event.ack = AsyncMock()
    event.bot = _bot()
    message = MagicMock()
    message.body.mid = "mid-pressed"
    event.message = message
    callback = MagicMock()
    callback.payload = payload
    callback.user.user_id = 42
    event.callback = callback
    return event


def _context() -> MemoryContext:
    return MemoryContext(chat_id=7, user_id=42)


def _keyboard_rows(attachment: object) -> list[list[object]]:
    return attachment.payload.buttons


@pytest.fixture
def content_service() -> MagicMock:
    service = MagicMock()
    service.get_emergency = AsyncMock(return_value=EmergencyContent(text="Аварийный текст"))
    service.get_services = AsyncMock(return_value=ServicesContent(text="Текст услуг"))
    service.get_payment = AsyncMock(
        return_value=PaymentContent(
            text="Текст оплаты",
            url="https://pay.example",
            button_text="Оплатить",
        )
    )
    service.get_contacts = AsyncMock(
        return_value=ContactsContent(
            text="Свяжитесь с нами",
            phones=[ContactPhone(title="Диспетчерская", phone="+7 (800) 000-00-01")],
        )
    )
    with patch("src.bot.handlers.menu.ContentService", return_value=service):
        yield service


@pytest.fixture
def welcome_service() -> MagicMock:
    service = MagicMock()
    service.get_message = AsyncMock(
        return_value=WelcomeMessage(text="Добро пожаловать", photo_token=None)
    )
    with patch("src.bot.handlers.menu.WelcomeService", return_value=service):
        yield service


@pytest.fixture
def client_service() -> MagicMock:
    service = MagicMock()
    service.list_tickets = AsyncMock(return_value=[])
    with patch("src.bot.handlers.menu.ClientTicketService", return_value=service):
        yield service


def _ticket(
    ticket_id: int,
    ticket_type: TicketType = TicketType.REQUEST,
    status: TicketStatus = TicketStatus.NEW,
    category_title: str | None = "Сантехника",
) -> SimpleNamespace:
    category = None if category_title is None else SimpleNamespace(title=category_title)
    return SimpleNamespace(id=ticket_id, type=ticket_type, status=status, category=category)


async def test_start_sends_welcome_with_main_menu(welcome_service: MagicMock):
    event = _message_created()
    context = _context()

    await menu.handle_start(event, context, MagicMock())

    assert await context.get_state() is None
    welcome_service.get_message.assert_awaited_once()
    kwargs = event.message.answer.await_args.kwargs
    assert kwargs["text"] == "Добро пожаловать"
    assert len(kwargs["attachments"]) == 1
    assert [
        [button.payload for button in row] for row in _keyboard_rows(kwargs["attachments"][0])
    ] == [
        ["form:start"],
        ["menu:question", "menu:tickets"],
        ["menu:payment", "menu:services"],
        ["menu:emergency"],
    ]


async def test_start_sends_photo_before_main_menu(welcome_service: MagicMock):
    welcome_service.get_message.return_value = WelcomeMessage(
        text="Добро пожаловать", photo_token="tok-1"
    )
    event = _message_created()

    await menu.handle_start(event, _context(), MagicMock())

    attachments = event.message.answer.await_args.kwargs["attachments"]
    assert len(attachments) == 2
    assert isinstance(attachments[0], AttachmentUpload)
    assert attachments[0].type == UploadType.IMAGE
    assert attachments[0].payload.token == "tok-1"
    assert len(_keyboard_rows(attachments[1])) == 4


async def test_start_retries_without_photo_when_max_rejects(welcome_service: MagicMock):
    welcome_service.get_message.return_value = WelcomeMessage(
        text="Добро пожаловать", photo_token="tok-1"
    )
    event = _message_created()
    event.message.answer = AsyncMock(side_effect=[MaxApiError(code=400, raw={}), None])

    await menu.handle_start(event, _context(), MagicMock())

    assert event.message.answer.await_count == 2
    first, second = event.message.answer.await_args_list
    assert first.kwargs["text"] == "Добро пожаловать"
    assert len(first.kwargs["attachments"]) == 2
    assert second.kwargs["text"] == "Добро пожаловать"
    assert len(second.kwargs["attachments"]) == 1
    assert not isinstance(second.kwargs["attachments"][0], AttachmentUpload)


async def test_start_without_photo_does_not_retry(welcome_service: MagicMock):
    event = _message_created()
    event.message.answer = AsyncMock(side_effect=MaxApiError(code=400, raw={}))

    with pytest.raises(MaxApiError):
        await menu.handle_start(event, _context(), MagicMock())

    event.message.answer.assert_awaited_once()


async def test_bot_started_sends_welcome_with_main_menu(welcome_service: MagicMock):
    event = _bot_started()
    context = _context()

    await menu.handle_bot_started(event, context, MagicMock())

    assert await context.get_state() is None
    kwargs = event.bot.send_message.await_args.kwargs
    assert kwargs["chat_id"] == 7
    assert kwargs["text"] == "Добро пожаловать"
    assert len(kwargs["attachments"]) == 1
    assert len(_keyboard_rows(kwargs["attachments"][0])) == 4


async def test_bot_started_sends_photo_before_main_menu(welcome_service: MagicMock):
    welcome_service.get_message.return_value = WelcomeMessage(
        text="Добро пожаловать", photo_token="tok-1"
    )
    event = _bot_started()

    await menu.handle_bot_started(event, _context(), MagicMock())

    attachments = event.bot.send_message.await_args.kwargs["attachments"]
    assert len(attachments) == 2
    assert isinstance(attachments[0], AttachmentUpload)
    assert attachments[0].payload.token == "tok-1"
    assert len(_keyboard_rows(attachments[1])) == 4


async def test_bot_started_retries_without_photo_when_max_rejects(welcome_service: MagicMock):
    welcome_service.get_message.return_value = WelcomeMessage(
        text="Добро пожаловать", photo_token="tok-1"
    )
    event = _bot_started()
    event.bot.send_message = AsyncMock(side_effect=[MaxApiError(code=400, raw={}), None])

    await menu.handle_bot_started(event, _context(), MagicMock())

    assert event.bot.send_message.await_count == 2
    first, second = event.bot.send_message.await_args_list
    assert first.kwargs["chat_id"] == 7
    assert len(first.kwargs["attachments"]) == 2
    assert second.kwargs["chat_id"] == 7
    assert len(second.kwargs["attachments"]) == 1
    assert not isinstance(second.kwargs["attachments"][0], AttachmentUpload)


async def test_emergency_callback_edits_with_section_text(content_service: MagicMock):
    event = _message_callback("menu:emergency")

    await menu.handle_emergency(event, MagicMock())

    assert event.edit.await_args.kwargs["text"] == "Аварийный текст"
    assert [
        row[0].payload for row in _keyboard_rows(event.edit.await_args.kwargs["attachments"][0])
    ] == ["menu:main"]


async def test_services_callback_edits_with_section_text(content_service: MagicMock):
    event = _message_callback("menu:services")

    await menu.handle_services(event, MagicMock())

    assert event.edit.await_args.kwargs["text"] == "Текст услуг"


async def test_payment_callback_edits_with_link_keyboard(content_service: MagicMock):
    event = _message_callback("menu:payment")

    await menu.handle_payment(event, MagicMock())

    rows = _keyboard_rows(event.edit.await_args.kwargs["attachments"][0])
    assert event.edit.await_args.kwargs["text"] == "Текст оплаты"
    assert rows[0][0].url == "https://pay.example"
    assert rows[1][0].payload == "menu:main"


async def test_main_callback_edits_with_welcome_and_main_menu(welcome_service: MagicMock):
    event = _message_callback("menu:main")

    await menu.handle_main(event, MagicMock())

    kwargs = event.edit.await_args.kwargs
    assert kwargs["text"] == "Добро пожаловать"
    assert len(kwargs["attachments"]) == 1
    assert len(_keyboard_rows(kwargs["attachments"][0])) == 4


async def test_main_callback_edits_with_photo(welcome_service: MagicMock):
    welcome_service.get_message.return_value = WelcomeMessage(
        text="Добро пожаловать", photo_token="tok-1"
    )
    event = _message_callback("menu:main")

    await menu.handle_main(event, MagicMock())

    attachments = event.edit.await_args.kwargs["attachments"]
    assert len(attachments) == 2
    assert isinstance(attachments[0], AttachmentUpload)
    assert attachments[0].payload.token == "tok-1"
    assert len(_keyboard_rows(attachments[1])) == 4


async def test_main_callback_retries_without_photo_when_max_rejects(welcome_service: MagicMock):
    welcome_service.get_message.return_value = WelcomeMessage(
        text="Добро пожаловать", photo_token="tok-1"
    )
    event = _message_callback("menu:main")
    event.edit = AsyncMock(side_effect=[MaxApiError(code=400, raw={}), None])

    await menu.handle_main(event, MagicMock())

    assert event.edit.await_count == 2
    first, second = event.edit.await_args_list
    assert first.kwargs["text"] == "Добро пожаловать"
    assert len(first.kwargs["attachments"]) == 2
    assert second.kwargs["text"] == "Добро пожаловать"
    assert len(second.kwargs["attachments"]) == 1
    assert not isinstance(second.kwargs["attachments"][0], AttachmentUpload)
    event.ack.assert_not_awaited()


async def test_main_callback_without_original_message_acks(welcome_service: MagicMock):
    event = _message_callback("menu:main")
    event.edit = AsyncMock(side_effect=ValueError("message is gone"))

    await menu.handle_main(event, MagicMock())

    event.ack.assert_awaited_once_with(notification=OUTDATED_BUTTON_TEXT)


async def test_main_callback_photo_fallback_without_original_message_acks(
    welcome_service: MagicMock,
):
    welcome_service.get_message.return_value = WelcomeMessage(
        text="Добро пожаловать", photo_token="tok-1"
    )
    event = _message_callback("menu:main")
    event.edit = AsyncMock(
        side_effect=[MaxApiError(code=400, raw={}), ValueError("message is gone")]
    )

    await menu.handle_main(event, MagicMock())

    assert event.edit.await_count == 2
    event.ack.assert_awaited_once_with(notification=OUTDATED_BUTTON_TEXT)


@pytest.mark.parametrize(
    ("getter", "handler"),
    [
        ("get_emergency", menu.handle_emergency),
        ("get_services", menu.handle_services),
        ("get_payment", menu.handle_payment),
    ],
)
async def test_missing_section_edits_with_placeholder(
    content_service: MagicMock,
    getter: str,
    handler: object,
):
    getattr(content_service, getter).return_value = None
    event = _message_callback()

    await handler(event, MagicMock())

    assert event.edit.await_args.kwargs["text"] == SECTION_EMPTY_TEXT
    assert [
        row[0].payload for row in _keyboard_rows(event.edit.await_args.kwargs["attachments"][0])
    ] == ["menu:main"]


@pytest.mark.parametrize(
    ("payload", "handler"),
    [
        ("menu:emergency", menu.handle_emergency),
        ("menu:services", menu.handle_services),
        ("menu:payment", menu.handle_payment),
        ("menu:question", menu.handle_question),
    ],
)
async def test_sections_edit_with_only_their_keyboard(
    content_service: MagicMock, payload: str, handler: object
):
    event = _message_callback(payload)

    await handler(event, MagicMock())

    attachments = event.edit.await_args.kwargs["attachments"]
    assert len(attachments) == 1
    assert not isinstance(attachments[0], AttachmentUpload)


@pytest.mark.parametrize("tickets", [[], [_ticket(1042)]])
async def test_my_tickets_edits_with_only_its_keyboard(
    client_service: MagicMock, tickets: list[SimpleNamespace]
):
    client_service.list_tickets.return_value = tickets
    event = _message_callback("menu:tickets")

    await menu.handle_my_tickets(event, MagicMock(), MagicMock())

    attachments = event.edit.await_args.kwargs["attachments"]
    assert len(attachments) == 1
    assert not isinstance(attachments[0], AttachmentUpload)


async def test_unknown_menu_payload_acks_with_notification():
    event = _message_callback("menu:unknown")

    await menu.handle_unknown_menu(event)

    event.edit.assert_not_awaited()
    event.ack.assert_awaited_once_with(notification=OUTDATED_BUTTON_TEXT)


async def test_callback_without_original_message_acks_with_notification(content_service: MagicMock):
    event = _message_callback("menu:emergency")
    event.edit = AsyncMock(side_effect=ValueError("message is gone"))

    await menu.handle_emergency(event, MagicMock())

    event.ack.assert_awaited_once_with(notification=OUTDATED_BUTTON_TEXT)


async def test_free_text_prompts_to_use_menu():
    event = _message_created()

    await menu.handle_free_text(event)

    assert event.message.answer.await_args.args[0] == USE_MENU_TEXT
    assert len(_keyboard_rows(event.message.answer.await_args.kwargs["attachments"][0])) == 4


async def test_my_tickets_edits_with_ticket_lines(client_service: MagicMock) -> None:
    client_service.list_tickets.return_value = [
        _ticket(1042, status=TicketStatus.IN_PROGRESS, category_title="Сантехника"),
        _ticket(
            1051,
            ticket_type=TicketType.QUESTION,
            status=TicketStatus.NEW,
            category_title=None,
        ),
        _ticket(1030, status=TicketStatus.CLOSED, category_title="Электрика"),
    ]
    event = _message_callback("menu:tickets")

    await menu.handle_my_tickets(event, MagicMock(), MagicMock())

    client_service.list_tickets.assert_awaited_once()
    assert event.edit.await_args.kwargs["text"] == (
        "Ваши заявки:\n\n"
        "№1042 · Сантехника — В работе\n"
        "№1051 · Вопрос — Принята\n"
        "№1030 · Электрика — Закрыта"
    )
    rows = _keyboard_rows(event.edit.await_args.kwargs["attachments"][0])
    assert [row[0].text for row in rows] == [
        "Написать по заявке №1042",
        "Написать по вопросу №1051",
        "« В меню",
    ]
    assert [row[0].payload for row in rows] == [
        "chat:ticket:1042",
        "chat:ticket:1051",
        "menu:main",
    ]


async def test_my_tickets_empty_edits_with_form_offer(client_service: MagicMock) -> None:
    event = _message_callback("menu:tickets")

    await menu.handle_my_tickets(event, MagicMock(), MagicMock())

    assert event.edit.await_args.kwargs["text"] == MY_TICKETS_EMPTY
    rows = _keyboard_rows(event.edit.await_args.kwargs["attachments"][0])
    assert [row[0].payload for row in rows] == ["form:start", "menu:main"]


async def test_my_tickets_only_closed_has_no_write_buttons(client_service: MagicMock) -> None:
    client_service.list_tickets.return_value = [
        _ticket(1030, status=TicketStatus.REJECTED, category_title="Электрика")
    ]
    event = _message_callback("menu:tickets")

    await menu.handle_my_tickets(event, MagicMock(), MagicMock())

    assert "№1030 · Электрика — Отклонена" in event.edit.await_args.kwargs["text"]
    rows = _keyboard_rows(event.edit.await_args.kwargs["attachments"][0])
    assert [row[0].payload for row in rows] == ["menu:main"]


async def test_my_tickets_callback_without_original_message_acks(
    client_service: MagicMock,
) -> None:
    event = _message_callback("menu:tickets")
    event.edit = AsyncMock(side_effect=ValueError("message is gone"))

    await menu.handle_my_tickets(event, MagicMock(), MagicMock())

    event.ack.assert_awaited_once_with(notification=OUTDATED_BUTTON_TEXT)


async def test_question_edits_with_contacts_and_phones(content_service: MagicMock) -> None:
    event = _message_callback("menu:question")

    await menu.handle_question(event, MagicMock())

    assert event.edit.await_args.kwargs["text"] == (
        "Свяжитесь с нами\n\nДиспетчерская: +7 (800) 000-00-01"
    )
    rows = _keyboard_rows(event.edit.await_args.kwargs["attachments"][0])
    assert [row[0].text for row in rows] == ["Написать вопрос", "« В меню"]
    assert [row[0].payload for row in rows] == ["question:write", "menu:main"]


async def test_question_without_phones_shows_only_text(content_service: MagicMock) -> None:
    content_service.get_contacts.return_value = ContactsContent(text="Свяжитесь с нами", phones=[])
    event = _message_callback("menu:question")

    await menu.handle_question(event, MagicMock())

    assert event.edit.await_args.kwargs["text"] == "Свяжитесь с нами"


async def test_question_missing_block_shows_default(content_service: MagicMock) -> None:
    content_service.get_contacts.return_value = None
    event = _message_callback("menu:question")

    await menu.handle_question(event, MagicMock())

    assert event.edit.await_args.kwargs["text"] == QUESTION_SECTION_DEFAULT
    rows = _keyboard_rows(event.edit.await_args.kwargs["attachments"][0])
    assert [row[0].payload for row in rows] == ["question:write", "menu:main"]


@pytest.mark.parametrize(
    "handler",
    [menu.handle_emergency, menu.handle_services, menu.handle_payment, menu.handle_question],
)
async def test_admin_sections_go_out_as_markdown(content_service: MagicMock, handler: object):
    event = _message_callback()

    await handler(event, MagicMock())

    assert event.edit.await_args.kwargs["format"] == ParseMode.MARKDOWN


async def test_welcome_goes_out_as_markdown(welcome_service: MagicMock):
    started = _bot_started()
    start = _message_created()
    main = _message_callback("menu:main")

    await menu.handle_bot_started(started, _context(), MagicMock())
    await menu.handle_start(start, _context(), MagicMock())
    await menu.handle_main(main, MagicMock())

    assert started.bot.send_message.await_args.kwargs["format"] == ParseMode.MARKDOWN
    assert start.message.answer.await_args.kwargs["format"] == ParseMode.MARKDOWN
    assert main.edit.await_args.kwargs["format"] == ParseMode.MARKDOWN


async def test_welcome_keeps_markdown_when_retried_without_photo(welcome_service: MagicMock):
    welcome_service.get_message.return_value = WelcomeMessage(
        text="Добро пожаловать", photo_token="token"
    )
    event = _message_created()
    event.message.answer = AsyncMock(side_effect=[MaxApiError(code=400, raw={}), None])

    await menu.handle_start(event, _context(), MagicMock())

    assert event.message.answer.await_args.kwargs["format"] == ParseMode.MARKDOWN


async def test_my_tickets_stay_plain_text(client_service: MagicMock):
    client_service.list_tickets.return_value = [_ticket(1042)]
    event = _message_callback("menu:tickets")

    await menu.handle_my_tickets(event, MagicMock(), MagicMock())

    assert event.edit.await_args.kwargs.get("format") is None


async def test_start_removes_stored_prompt_keyboard(welcome_service: MagicMock) -> None:
    event = _message_created()
    context = _context()
    await context.set_state("state")
    await context.update_data(prompt_mid="mid-old")

    await menu.handle_start(event, context, MagicMock())

    event.bot.edit_message.assert_awaited_once_with(message_id="mid-old", attachments=[])
    assert await context.get_state() is None
    assert await context.get_data() == {}


async def test_bot_started_removes_stored_prompt_keyboard(welcome_service: MagicMock) -> None:
    event = _bot_started()
    context = _context()
    await context.set_state("state")
    await context.update_data(prompt_mid="mid-old")

    await menu.handle_bot_started(event, context, MagicMock())

    event.bot.edit_message.assert_awaited_once_with(message_id="mid-old", attachments=[])
    assert await context.get_state() is None


async def test_main_menu_acks_then_sends_new_welcome(welcome_service: MagicMock) -> None:
    event = _message_callback(MENU_START)
    context = _context()
    await context.set_state("state")
    await context.update_data(prompt_mid="mid-old")

    await menu.handle_main_menu(event, context, MagicMock())

    event.ack.assert_awaited_once_with(notification=MAIN_MENU_BUTTON)
    names = [call[0] for call in event.mock_calls]
    assert names.index("ack") < names.index("bot.send_message")
    event.bot.edit_message.assert_awaited_once_with(message_id="mid-old", attachments=[])
    assert await context.get_state() is None
    assert await context.get_data() == {}
    event.edit.assert_not_awaited()
    kwargs = event.bot.send_message.await_args.kwargs
    assert kwargs["user_id"] == 42
    assert kwargs["text"] == "Добро пожаловать"
    assert kwargs["format"] == ParseMode.MARKDOWN
    assert len(kwargs["attachments"]) == 1


async def test_main_menu_sends_welcome_with_photo(welcome_service: MagicMock) -> None:
    welcome_service.get_message.return_value = WelcomeMessage(
        text="Добро пожаловать", photo_token="tok-1"
    )
    event = _message_callback(MENU_START)

    await menu.handle_main_menu(event, _context(), MagicMock())

    attachments = event.bot.send_message.await_args.kwargs["attachments"]
    assert len(attachments) == 2
    assert isinstance(attachments[0], AttachmentUpload)
    assert attachments[0].payload.token == "tok-1"
    assert len(_keyboard_rows(attachments[1])) == 4
    event.edit.assert_not_awaited()


async def test_main_menu_retries_without_photo_when_max_rejects(
    welcome_service: MagicMock,
) -> None:
    welcome_service.get_message.return_value = WelcomeMessage(
        text="Добро пожаловать", photo_token="tok-1"
    )
    event = _message_callback(MENU_START)
    event.bot.send_message = AsyncMock(side_effect=[MaxApiError(code=400, raw={}), None])

    await menu.handle_main_menu(event, _context(), MagicMock())

    assert event.bot.send_message.await_count == 2
    first, second = event.bot.send_message.await_args_list
    assert first.kwargs["user_id"] == 42
    assert len(first.kwargs["attachments"]) == 2
    assert second.kwargs["user_id"] == 42
    assert len(second.kwargs["attachments"]) == 1
    assert not isinstance(second.kwargs["attachments"][0], AttachmentUpload)


def test_main_menu_handler_registered_before_unknown_menu() -> None:
    funcs = [handler.func_event for handler in menu.router.event_handlers]

    assert funcs.index(menu.handle_main_menu) < funcs.index(menu.handle_unknown_menu)
