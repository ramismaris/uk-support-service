import logging
from collections.abc import Awaitable, Callable
from functools import partial

from maxapi import Router
from maxapi.context import BaseContext
from maxapi.exceptions import MaxApiError
from maxapi.filters import F
from maxapi.filters.command import CommandStart
from maxapi.types import BotStarted, MessageCallback, MessageCreated
from maxapi.types.attachments import AttachmentButton
from maxapi.types.attachments.upload import AttachmentUpload
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards import (
    MENU_EMERGENCY,
    MENU_MAIN,
    MENU_PAYMENT,
    MENU_PREFIX,
    MENU_QUESTION,
    MENU_SERVICES,
    MENU_TICKETS,
    back_keyboard,
    contacts_keyboard,
    main_menu_keyboard,
    my_tickets_empty_keyboard,
    my_tickets_keyboard,
    payment_keyboard,
    photo_attachment,
)
from src.core.texts import (
    MY_TICKETS_EMPTY,
    MY_TICKETS_TITLE,
    OUTDATED_BUTTON_TEXT,
    QUESTION_SECTION_DEFAULT,
    SECTION_EMPTY_TEXT,
    STATUS_LABELS,
    USE_MENU_TEXT,
    ticket_button_label,
)
from src.models.user import User
from src.providers.factory import get_messenger_provider, get_storage_provider
from src.schemas.content import ContactsContent
from src.services.client_ticket_service import ClientTicketService
from src.services.content_service import ContentService
from src.services.welcome_service import WelcomeService

logger = logging.getLogger(__name__)

router = Router("menu")

Attachment = AttachmentButton | AttachmentUpload


def _service(db: AsyncSession) -> ClientTicketService:
    return ClientTicketService(db, get_messenger_provider(), get_storage_provider())


def _welcome_service(db: AsyncSession) -> WelcomeService:
    return WelcomeService(db, get_messenger_provider(), get_storage_provider())


def _tickets_text(tickets: list) -> str:
    lines = [MY_TICKETS_TITLE, ""]
    for ticket in tickets:
        category_title = ticket.category.title if ticket.category else None
        label = ticket_button_label(ticket.type, ticket.id, category_title)
        lines.append(f"{label} — {STATUS_LABELS[ticket.status]}")
    return "\n".join(lines)


def _contacts_text(content: ContactsContent) -> str:
    lines = [content.text]
    if content.phones:
        lines.append("")
        lines.extend(f"{phone.title}: {phone.phone}" for phone in content.phones)
    return "\n".join(lines)


async def _welcome(db: AsyncSession) -> tuple[str, list[Attachment]]:
    message = await _welcome_service(db).get_message()
    if message.photo_token is None:
        return message.text, [main_menu_keyboard()]
    return message.text, [photo_attachment(message.photo_token), main_menu_keyboard()]


def _has_photo(attachments: list[Attachment]) -> bool:
    return any(isinstance(attachment, AttachmentUpload) for attachment in attachments)


def _log_photo_rejected(exc: MaxApiError) -> None:
    logger.warning(
        "Max rejected the welcome with a photo (code %s); answering without it", exc.code
    )


async def _send_welcome(
    send: Callable[..., Awaitable[object]], text: str, attachments: list[Attachment]
) -> None:
    try:
        await send(text=text, attachments=attachments)
    except MaxApiError as exc:
        if not _has_photo(attachments):
            raise
        _log_photo_rejected(exc)
        await send(text=text, attachments=[main_menu_keyboard()])


async def _edit(event: MessageCallback, text: str, attachments: list[Attachment]) -> None:
    try:
        await event.edit(text=text, attachments=attachments)
    except MaxApiError as exc:
        if not _has_photo(attachments):
            raise
        _log_photo_rejected(exc)
        await _edit(event, text, [main_menu_keyboard()])
    except ValueError:
        await event.ack(notification=OUTDATED_BUTTON_TEXT)


@router.bot_started()
async def handle_bot_started(event: BotStarted, context: BaseContext, db: AsyncSession) -> None:
    await context.clear()
    text, attachments = await _welcome(db)
    await _send_welcome(partial(event.bot.send_message, chat_id=event.chat_id), text, attachments)


@router.message_created(CommandStart())
async def handle_start(event: MessageCreated, context: BaseContext, db: AsyncSession) -> None:
    await context.clear()
    text, attachments = await _welcome(db)
    await _send_welcome(event.message.answer, text, attachments)


@router.message_callback(F.callback.payload == MENU_EMERGENCY)
async def handle_emergency(event: MessageCallback, db: AsyncSession) -> None:
    content = await ContentService(db).get_emergency()
    text = content.text if content is not None else SECTION_EMPTY_TEXT
    await _edit(event, text, [back_keyboard()])


@router.message_callback(F.callback.payload == MENU_SERVICES)
async def handle_services(event: MessageCallback, db: AsyncSession) -> None:
    content = await ContentService(db).get_services()
    text = content.text if content is not None else SECTION_EMPTY_TEXT
    await _edit(event, text, [back_keyboard()])


@router.message_callback(F.callback.payload == MENU_PAYMENT)
async def handle_payment(event: MessageCallback, db: AsyncSession) -> None:
    content = await ContentService(db).get_payment()
    if content is None:
        await _edit(event, SECTION_EMPTY_TEXT, [back_keyboard()])
        return
    await _edit(event, content.text, [payment_keyboard(content)])


@router.message_callback(F.callback.payload == MENU_TICKETS)
async def handle_my_tickets(event: MessageCallback, db: AsyncSession, user: User) -> None:
    tickets = await _service(db).list_tickets(user)
    if not tickets:
        await _edit(event, MY_TICKETS_EMPTY, [my_tickets_empty_keyboard()])
        return
    await _edit(event, _tickets_text(tickets), [my_tickets_keyboard(tickets)])


@router.message_callback(F.callback.payload == MENU_QUESTION)
async def handle_question(event: MessageCallback, db: AsyncSession) -> None:
    content = await ContentService(db).get_contacts()
    if content is None:
        await _edit(event, QUESTION_SECTION_DEFAULT, [contacts_keyboard()])
        return
    await _edit(event, _contacts_text(content), [contacts_keyboard()])


@router.message_callback(F.callback.payload == MENU_MAIN)
async def handle_main(event: MessageCallback, db: AsyncSession) -> None:
    text, attachments = await _welcome(db)
    await _edit(event, text, attachments)


@router.message_callback(F.callback.payload.regexp(rf"^{MENU_PREFIX}"))
async def handle_unknown_menu(event: MessageCallback) -> None:
    await event.ack(notification=OUTDATED_BUTTON_TEXT)


@router.message_created()
async def handle_free_text(event: MessageCreated) -> None:
    await event.message.answer(USE_MENU_TEXT, attachments=[main_menu_keyboard()])
