from maxapi import Router
from maxapi.filters.command import Command
from maxapi.types import MessageCreated

from src.core.texts import ID_TEXT

router = Router("start")


@router.message_created(Command("id"))
async def handle_id(event: MessageCreated) -> None:
    sender = event.message.sender
    if sender is None:
        return
    await event.message.answer(ID_TEXT.format(user_id=sender.user_id))
