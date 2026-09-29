import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import ClientError
from maxapi.context import MemoryContext
from maxapi.enums.parse_mode import ParseMode
from maxapi.exceptions import MaxApiError, MaxConnection
from maxapi.types import BotStarted, MessageCallback, MessageCreated

from src.bot import prompts
from src.bot.keyboards import menu_button_keyboard
from src.core.texts import OUTDATED_BUTTON_TEXT


def _sent(mid: str) -> SimpleNamespace:
    return SimpleNamespace(message=SimpleNamespace(body=SimpleNamespace(mid=mid)))


def _bot() -> MagicMock:
    bot = MagicMock()
    bot.edit_message = AsyncMock(return_value=SimpleNamespace(success=True))
    return bot


def _message(mid: str) -> MagicMock:
    event = MagicMock(spec=MessageCreated)
    event.bot = _bot()
    message = MagicMock()
    message.body.mid = mid
    message.answer = AsyncMock(return_value=_sent(mid))
    event.message = message
    return event


def _press(mid: str) -> MagicMock:
    event = MagicMock(spec=MessageCallback)
    event.bot = _bot()
    event.edit = AsyncMock()
    event.ack = AsyncMock()
    message = MagicMock()
    message.body.mid = mid
    event.message = message
    callback = MagicMock()
    callback.payload = "menu:start"
    event.callback = callback
    return event


def _started() -> MagicMock:
    event = MagicMock(spec=BotStarted)
    event.bot = _bot()
    return event


def _context() -> MemoryContext:
    return MemoryContext(chat_id=7, user_id=42)


async def test_show_prompt_message_without_previous() -> None:
    event = _message("mid-new")
    context = _context()
    keyboard = menu_button_keyboard()

    await prompts.show_prompt(event, context, "text", keyboard)

    event.message.answer.assert_awaited_once_with("text", attachments=[keyboard], format=None)
    assert (await context.get_data())[prompts.PROMPT_MID] == "mid-new"
    event.bot.edit_message.assert_not_awaited()


async def test_show_prompt_message_removes_previous_after_answering() -> None:
    event = _message("mid-new")
    context = _context()
    await context.update_data(**{prompts.PROMPT_MID: "mid-old"})
    order: list[str] = []
    event.message.answer.side_effect = lambda *args, **kwargs: (
        order.append("answer") or _sent("mid-new")
    )
    event.bot.edit_message.side_effect = lambda **kwargs: (
        order.append("edit") or SimpleNamespace(success=True)
    )

    await prompts.show_prompt(event, context, "text", menu_button_keyboard())

    event.bot.edit_message.assert_awaited_once_with(message_id="mid-old", attachments=[])
    assert "text" not in event.bot.edit_message.await_args.kwargs
    assert order == ["answer", "edit"]
    assert (await context.get_data())[prompts.PROMPT_MID] == "mid-new"


async def test_show_prompt_press_on_stored_prompt_does_not_remove() -> None:
    event = _press("mid-pressed")
    context = _context()
    await context.update_data(**{prompts.PROMPT_MID: "mid-pressed"})
    keyboard = menu_button_keyboard()

    await prompts.show_prompt(event, context, "text", keyboard)

    event.edit.assert_awaited_once_with(text="text", attachments=[keyboard], format=None)
    event.bot.edit_message.assert_not_awaited()
    assert (await context.get_data())[prompts.PROMPT_MID] == "mid-pressed"


async def test_show_prompt_passes_parse_mode_to_message() -> None:
    event = _message("mid-new")
    context = _context()
    keyboard = menu_button_keyboard()

    await prompts.show_prompt(event, context, "text", keyboard, parse_mode=ParseMode.HTML)

    event.message.answer.assert_awaited_once_with(
        "text", attachments=[keyboard], format=ParseMode.HTML
    )


async def test_show_prompt_passes_parse_mode_to_edit() -> None:
    event = _press("mid-pressed")
    context = _context()
    keyboard = menu_button_keyboard()

    await prompts.show_prompt(event, context, "text", keyboard, parse_mode=ParseMode.HTML)

    event.edit.assert_awaited_once_with(text="text", attachments=[keyboard], format=ParseMode.HTML)


async def test_show_prompt_press_on_other_message_removes_previous() -> None:
    event = _press("mid-pressed")
    context = _context()
    await context.update_data(**{prompts.PROMPT_MID: "mid-old"})

    await prompts.show_prompt(event, context, "text", menu_button_keyboard())

    event.edit.assert_awaited_once()
    event.bot.edit_message.assert_awaited_once_with(message_id="mid-old", attachments=[])
    assert (await context.get_data())[prompts.PROMPT_MID] == "mid-pressed"


async def test_show_prompt_press_on_deleted_message_acks_only() -> None:
    event = _press("mid-pressed")
    event.edit.side_effect = ValueError("message is gone")
    context = _context()
    await context.update_data(**{prompts.PROMPT_MID: "mid-old"})

    await prompts.show_prompt(event, context, "text", menu_button_keyboard())

    event.ack.assert_awaited_once_with(notification=OUTDATED_BUTTON_TEXT)
    event.bot.edit_message.assert_not_awaited()
    assert (await context.get_data())[prompts.PROMPT_MID] == "mid-old"


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(MaxApiError(400, {}), id="max-api"),
        pytest.param(MaxConnection(), id="max-connection"),
        pytest.param(ClientError(), id="client-error"),
        pytest.param(TimeoutError(), id="timeout"),
    ],
)
async def test_show_prompt_removal_error_is_logged(
    error: BaseException, caplog: pytest.LogCaptureFixture
) -> None:
    event = _message("mid-new")
    context = _context()
    await context.update_data(**{prompts.PROMPT_MID: "mid-old"})
    event.bot.edit_message.side_effect = error

    with caplog.at_level(logging.WARNING, logger="src.bot.prompts"):
        await prompts.show_prompt(event, context, "text", menu_button_keyboard())

    assert "mid-old" in caplog.text
    assert type(error).__name__ in caplog.text
    assert (await context.get_data())[prompts.PROMPT_MID] == "mid-new"


async def test_show_prompt_removal_success_false_is_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    event = _message("mid-new")
    context = _context()
    await context.update_data(**{prompts.PROMPT_MID: "mid-old"})
    event.bot.edit_message.return_value = SimpleNamespace(success=False)

    with caplog.at_level(logging.WARNING, logger="src.bot.prompts"):
        await prompts.show_prompt(event, context, "text", menu_button_keyboard())

    assert "mid-old" in caplog.text
    assert (await context.get_data())[prompts.PROMPT_MID] == "mid-new"


async def test_show_prompt_send_failure_keeps_old_prompt() -> None:
    event = _message("mid-new")
    context = _context()
    await context.update_data(**{prompts.PROMPT_MID: "mid-old"})
    event.message.answer.side_effect = RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await prompts.show_prompt(event, context, "text", menu_button_keyboard())

    event.bot.edit_message.assert_not_awaited()
    assert (await context.get_data())[prompts.PROMPT_MID] == "mid-old"


async def test_end_dialog_message_clears_and_removes_keyboard() -> None:
    event = _message("mid-any")
    context = _context()
    await context.set_state("state")
    await context.update_data(**{prompts.PROMPT_MID: "mid-old", "kept": 1})

    await prompts.end_dialog(event, context)

    assert await context.get_state() is None
    assert await context.get_data() == {}
    event.bot.edit_message.assert_awaited_once_with(message_id="mid-old", attachments=[])


async def test_end_dialog_press_on_stored_prompt_does_not_remove() -> None:
    event = _press("mid-old")
    context = _context()
    await context.update_data(**{prompts.PROMPT_MID: "mid-old"})

    await prompts.end_dialog(event, context)

    event.bot.edit_message.assert_not_awaited()
    assert await context.get_data() == {}


async def test_end_dialog_press_on_other_message_removes() -> None:
    event = _press("mid-pressed")
    context = _context()
    await context.update_data(**{prompts.PROMPT_MID: "mid-old"})

    await prompts.end_dialog(event, context)

    event.bot.edit_message.assert_awaited_once_with(message_id="mid-old", attachments=[])


async def test_end_dialog_bot_started_removes_keyboard() -> None:
    event = _started()
    context = _context()
    await context.update_data(**{prompts.PROMPT_MID: "mid-old"})

    await prompts.end_dialog(event, context)

    event.bot.edit_message.assert_awaited_once_with(message_id="mid-old", attachments=[])


async def test_end_dialog_without_prompt_only_clears() -> None:
    event = _message("mid-any")
    context = _context()
    await context.set_state("state")

    await prompts.end_dialog(event, context)

    event.bot.edit_message.assert_not_awaited()
    assert await context.get_state() is None
    assert await context.get_data() == {}


async def test_end_dialog_removal_failure_still_clears() -> None:
    event = _message("mid-any")
    context = _context()
    await context.set_state("state")
    await context.update_data(**{prompts.PROMPT_MID: "mid-old"})
    event.bot.edit_message.side_effect = MaxConnection()

    await prompts.end_dialog(event, context)

    assert await context.get_state() is None
    assert await context.get_data() == {}
