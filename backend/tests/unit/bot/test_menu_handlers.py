from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from maxapi.types import BotStarted, MessageCallback, MessageCreated

from src.bot.handlers import menu
from src.core.texts import (
    OUTDATED_BUTTON_TEXT,
    SECTION_EMPTY_TEXT,
    START_TEXT,
    USE_MENU_TEXT,
)
from src.schemas.content import (
    EmergencyContent,
    PaymentContent,
    ServicesContent,
    WelcomeContent,
)


def _message_created() -> MagicMock:
    event = MagicMock(spec=MessageCreated)
    message = MagicMock()
    message.answer = AsyncMock()
    event.message = message
    return event


def _bot_started() -> MagicMock:
    event = MagicMock(spec=BotStarted)
    event.chat_id = 7
    event.bot = MagicMock()
    event.bot.send_message = AsyncMock()
    return event


def _message_callback(payload: str = "menu:emergency") -> MagicMock:
    event = MagicMock(spec=MessageCallback)
    event.edit = AsyncMock()
    event.ack = AsyncMock()
    callback = MagicMock()
    callback.payload = payload
    event.callback = callback
    return event


def _keyboard_rows(attachment: object) -> list[list[object]]:
    return attachment.payload.buttons


@pytest.fixture
def content_service() -> MagicMock:
    service = MagicMock()
    service.get_welcome = AsyncMock(return_value=WelcomeContent(text="Добро пожаловать"))
    service.get_emergency = AsyncMock(return_value=EmergencyContent(text="Аварийный текст"))
    service.get_services = AsyncMock(return_value=ServicesContent(text="Текст услуг"))
    service.get_payment = AsyncMock(
        return_value=PaymentContent(
            text="Текст оплаты",
            url="https://pay.example",
            button_text="Оплатить",
        )
    )
    with patch("src.bot.handlers.menu.ContentService", return_value=service):
        yield service


async def test_start_sends_welcome_with_main_menu(content_service: MagicMock):
    event = _message_created()

    await menu.handle_start(event, MagicMock())

    content_service.get_welcome.assert_awaited_once()
    kwargs = event.message.answer.await_args.kwargs
    assert event.message.answer.await_args.args[0] == "Добро пожаловать"
    assert [row[0].payload for row in _keyboard_rows(kwargs["attachments"][0])] == [
        "menu:emergency",
        "menu:services",
        "menu:payment",
    ]


async def test_start_uses_fallback_without_welcome_block(content_service: MagicMock):
    content_service.get_welcome.return_value = None
    event = _message_created()

    await menu.handle_start(event, MagicMock())

    assert event.message.answer.await_args.args[0] == START_TEXT


async def test_bot_started_sends_welcome_with_main_menu(content_service: MagicMock):
    event = _bot_started()

    await menu.handle_bot_started(event, MagicMock())

    kwargs = event.bot.send_message.await_args.kwargs
    assert kwargs["chat_id"] == 7
    assert kwargs["text"] == "Добро пожаловать"
    assert len(_keyboard_rows(kwargs["attachments"][0])) == 3


async def test_bot_started_uses_fallback_without_welcome_block(content_service: MagicMock):
    content_service.get_welcome.return_value = None
    event = _bot_started()

    await menu.handle_bot_started(event, MagicMock())

    assert event.bot.send_message.await_args.kwargs["text"] == START_TEXT


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


async def test_main_callback_edits_with_welcome_and_main_menu(content_service: MagicMock):
    event = _message_callback("menu:main")

    await menu.handle_main(event, MagicMock())

    assert event.edit.await_args.kwargs["text"] == "Добро пожаловать"
    assert len(_keyboard_rows(event.edit.await_args.kwargs["attachments"][0])) == 3


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
    assert len(_keyboard_rows(event.message.answer.await_args.kwargs["attachments"][0])) == 3
