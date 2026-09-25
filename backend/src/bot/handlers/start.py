from maxapi import Router
from maxapi.filters.command import Command, CommandStart
from maxapi.types import BotStarted, MessageCreated

from src.core.texts import ID_TEXT, START_TEXT

router = Router("start")


@router.bot_started()
async def handle_bot_started(event: BotStarted) -> None:
    await event.bot.send_message(chat_id=event.chat_id, text=START_TEXT)


@router.message_created(CommandStart())
async def handle_start(event: MessageCreated) -> None:
    await event.message.answer(START_TEXT)


@router.message_created(Command("id"))
async def handle_id(event: MessageCreated) -> None:
    sender = event.message.sender
    if sender is None:
        return
    await event.message.answer(ID_TEXT.format(user_id=sender.user_id))
