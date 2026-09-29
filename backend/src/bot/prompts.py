import logging

from aiohttp import ClientError
from maxapi.context import BaseContext
from maxapi.enums.parse_mode import ParseMode
from maxapi.exceptions import MaxError
from maxapi.types import BotStarted, MessageCallback, MessageCreated
from maxapi.types.attachments import AttachmentButton

from src.core.texts import OUTDATED_BUTTON_TEXT

logger = logging.getLogger(__name__)

PROMPT_MID = "prompt_mid"


async def _remove_keyboard(bot, message_id: str) -> None:
    try:
        result = await bot.edit_message(message_id=message_id, attachments=[])
    except (MaxError, ClientError, TimeoutError) as exc:
        logger.warning(
            "Failed to remove keyboard from message %s: %s", message_id, type(exc).__name__
        )
        return
    if result is not None and not result.success:
        logger.warning("Failed to remove keyboard from message %s: success=false", message_id)


def _pressed_mid(event: MessageCallback) -> str | None:
    if event.message is None or event.message.body is None:
        return None
    return event.message.body.mid


async def show_prompt(
    event: MessageCreated | MessageCallback,
    context: BaseContext,
    text: str,
    keyboard: AttachmentButton,
    *,
    parse_mode: ParseMode | None = None,
) -> None:
    if isinstance(event, MessageCallback):
        try:
            await event.edit(text=text, attachments=[keyboard], format=parse_mode)
        except ValueError:
            await event.ack(notification=OUTDATED_BUTTON_TEXT)
            return
        new_mid = _pressed_mid(event)
    else:
        sent = await event.message.answer(text, attachments=[keyboard], format=parse_mode)
        new_mid = sent.message.body.mid

    old_mid = (await context.get_data()).get(PROMPT_MID)
    await context.update_data(**{PROMPT_MID: new_mid})
    if old_mid is not None and old_mid != new_mid:
        await _remove_keyboard(event.bot, old_mid)


async def end_dialog(
    event: MessageCreated | MessageCallback | BotStarted, context: BaseContext
) -> None:
    old_mid = (await context.get_data()).get(PROMPT_MID)
    await context.clear()
    if old_mid is None:
        return
    if isinstance(event, MessageCallback) and _pressed_mid(event) == old_mid:
        return
    await _remove_keyboard(event.bot, old_mid)
