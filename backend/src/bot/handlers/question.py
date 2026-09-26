from maxapi import Router
from maxapi.context import BaseContext
from maxapi.filters import F
from maxapi.types import MessageCallback, MessageCreated
from maxapi.types.attachments import AttachmentButton
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards import (
    QUESTION_CANCEL,
    QUESTION_PREFIX,
    QUESTION_WRITE,
    main_menu_keyboard,
    question_cancel_keyboard,
)
from src.bot.states import QuestionForm
from src.bot.utils import NOT_A_COMMAND, image_urls, message_text
from src.core.exceptions import AppException
from src.core.texts import (
    CHAT_PHOTOS_FAILED,
    FORM_PHOTOS_MAX,
    OUTDATED_BUTTON_TEXT,
    QUESTION_CANCELLED,
    QUESTION_PROMPT,
    QUESTION_SENT,
    QUESTION_TEXT_REQUIRED,
)
from src.models.user import User
from src.providers.factory import get_messenger_provider, get_storage_provider
from src.services.client_ticket_service import ClientTicketService, validate_description

router = Router("question")


def _service(db: AsyncSession) -> ClientTicketService:
    return ClientTicketService(db, get_messenger_provider(), get_storage_provider())


async def _edit(event: MessageCallback, text: str, keyboard: AttachmentButton) -> None:
    try:
        await event.edit(text=text, attachments=[keyboard])
    except ValueError:
        await event.ack(notification=OUTDATED_BUTTON_TEXT)


@router.message_callback(F.callback.payload == QUESTION_WRITE)
async def handle_write(event: MessageCallback, context: BaseContext) -> None:
    await context.clear()
    await context.set_state(QuestionForm.text)
    await _edit(event, QUESTION_PROMPT, question_cancel_keyboard())


@router.message_created(QuestionForm.text, NOT_A_COMMAND)
async def handle_question(
    event: MessageCreated, context: BaseContext, db: AsyncSession, user: User
) -> None:
    text = message_text(event.message)
    if not text:
        await event.message.answer(QUESTION_TEXT_REQUIRED, attachments=[question_cancel_keyboard()])
        return
    try:
        description = validate_description(text)
    except AppException as exc:
        await event.message.answer(exc.message, attachments=[question_cancel_keyboard()])
        return

    service = _service(db)
    file_ids: list[int] = []
    failed = 0
    for url in image_urls(event.message)[:FORM_PHOTOS_MAX]:
        try:
            photo = await service.save_photo(url)
        except AppException:
            failed += 1
            continue
        file_ids.append(photo.id)

    try:
        ticket = await service.create_question(user, description=description, photo_ids=file_ids)
    except AppException as exc:
        await event.message.answer(exc.message, attachments=[question_cancel_keyboard()])
        return
    await context.clear()
    await event.message.answer(QUESTION_SENT.format(ticket_id=ticket.id))
    if failed:
        await event.message.answer(CHAT_PHOTOS_FAILED)


@router.message_callback(F.callback.payload == QUESTION_CANCEL, QuestionForm.text)
async def handle_cancel(event: MessageCallback, context: BaseContext) -> None:
    await context.clear()
    await _edit(event, QUESTION_CANCELLED, main_menu_keyboard())


@router.message_callback(F.callback.payload.regexp(rf"^{QUESTION_PREFIX}"))
async def handle_stale_callback(event: MessageCallback) -> None:
    await event.ack(notification=OUTDATED_BUTTON_TEXT)
