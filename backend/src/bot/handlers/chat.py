from maxapi import Router
from maxapi.context import BaseContext
from maxapi.enums.message_link_type import MessageLinkType
from maxapi.filters import F
from maxapi.types import MessageCallback, MessageCreated
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards import (
    CHAT_CANCEL,
    CHAT_CHOOSE_PREFIX,
    CHAT_PREFIX,
    CHAT_QUESTION,
    choose_ticket_keyboard,
    confirm_question_keyboard,
    main_menu_keyboard,
)
from src.bot.states import ChatStates
from src.bot.utils import NOT_A_COMMAND, image_urls, message_text, parse_id
from src.core.constants import CHAT_TICKET_PREFIX
from src.core.exceptions import AppException
from src.core.texts import (
    CHAT_CHOOSE_TICKET,
    CHAT_FINISH_CURRENT,
    CHAT_NOT_SENT,
    CHAT_OFFER_QUESTION,
    CHAT_PHOTOS_ALL_FAILED,
    CHAT_PHOTOS_FAILED,
    CHAT_SENT,
    CHAT_TEXT_REQUIRED,
    CHAT_UNSUPPORTED,
    CHAT_WRITE_NOTIFICATION,
    CHAT_WRITE_PROMPT,
    FORM_PHOTOS_MAX,
    OUTDATED_BUTTON_TEXT,
    QUESTION_SENT,
    ticket_dative,
)
from src.models.user import User
from src.providers.factory import get_messenger_provider, get_storage_provider
from src.services.client_ticket_service import ClientTicketService
from src.services.message_service import MessageService
from src.services.ticket_rules import OfferNewQuestion, ToTicket

router = Router("chat")


def _client_service(db: AsyncSession) -> ClientTicketService:
    return ClientTicketService(db, get_messenger_provider(), get_storage_provider())


def _message_service(db: AsyncSession) -> MessageService:
    return MessageService(db, get_messenger_provider(), get_storage_provider())


def _reply_mid(message) -> str | None:
    if message.link is None or message.link.type != MessageLinkType.REPLY:
        return None
    return message.link.message.mid


def _message_mid(message) -> str | None:
    if message.body is None:
        return None
    return message.body.mid


async def _save_photos(service: ClientTicketService, urls: list[str]) -> tuple[list[int], int]:
    file_ids: list[int] = []
    failed = 0
    for url in urls:
        try:
            photo = await service.save_photo(url)
        except AppException:
            failed += 1
            continue
        file_ids.append(photo.id)
    return file_ids, failed


async def _edit(event: MessageCallback, text: str) -> None:
    try:
        await event.edit(text=text, attachments=[])
    except ValueError:
        await event.ack(notification=OUTDATED_BUTTON_TEXT)


@router.message_created(None, NOT_A_COMMAND)
async def handle_free_message(
    event: MessageCreated, context: BaseContext, db: AsyncSession, user: User
) -> None:
    text = message_text(event.message)
    urls = image_urls(event.message)[:FORM_PHOTOS_MAX]
    mid = _message_mid(event.message)
    reply_mid = _reply_mid(event.message)

    if not text and not urls:
        await event.message.answer(CHAT_UNSUPPORTED)
        return

    message_service = _message_service(db)
    client_service = _client_service(db)
    decision = await message_service.resolve_client_route(user, reply_mid)

    if isinstance(decision, OfferNewQuestion):
        if not text:
            await event.message.answer(CHAT_TEXT_REQUIRED, attachments=[main_menu_keyboard()])
            return
        file_ids, _ = await _save_photos(client_service, urls)
        await context.update_data(text=text, file_ids=file_ids, max_message_id=mid)
        await context.set_state(ChatStates.confirm_question)
        await event.message.answer(CHAT_OFFER_QUESTION, attachments=[confirm_question_keyboard()])
        return

    if isinstance(decision, ToTicket):
        file_ids, failed = await _save_photos(client_service, urls)
        if failed and not file_ids and not text:
            await event.message.answer(CHAT_PHOTOS_ALL_FAILED)
            return
        try:
            await message_service.add_client_message(
                user,
                decision.ticket_id,
                text=text or None,
                file_ids=file_ids,
                max_message_id=mid,
            )
        except AppException as exc:
            await event.message.answer(exc.message)
            return
        ticket = await client_service.get_ticket(user, decision.ticket_id)
        await event.message.answer(CHAT_SENT.format(label=ticket_dative(ticket.type, ticket.id)))
        if failed:
            await event.message.answer(CHAT_PHOTOS_FAILED)
        return

    file_ids, failed = await _save_photos(client_service, urls)
    if failed and not file_ids and not text:
        await event.message.answer(CHAT_PHOTOS_ALL_FAILED)
        return
    await context.update_data(text=text, file_ids=file_ids, max_message_id=mid)
    await context.set_state(ChatStates.choose_ticket)
    tickets = await client_service.list_open_tickets(user)
    by_id = {ticket.id: ticket for ticket in tickets}
    ordered = [by_id[ticket_id] for ticket_id in decision.ticket_ids if ticket_id in by_id]
    await event.message.answer(
        CHAT_CHOOSE_TICKET,
        attachments=[choose_ticket_keyboard(ordered, with_question=bool(text))],
    )


@router.message_created(ChatStates, NOT_A_COMMAND)
async def handle_pending_message(
    event: MessageCreated, context: BaseContext, db: AsyncSession, user: User
) -> None:
    state = await context.get_state()
    if state == ChatStates.choose_ticket:
        data = await context.get_data()
        tickets = await _client_service(db).list_open_tickets(user)
        await event.message.answer(
            CHAT_CHOOSE_TICKET,
            attachments=[choose_ticket_keyboard(tickets, with_question=bool(data.get("text")))],
        )
    elif state == ChatStates.confirm_question:
        await event.message.answer(CHAT_OFFER_QUESTION, attachments=[confirm_question_keyboard()])


@router.message_callback(
    F.callback.payload.regexp(rf"^{CHAT_CHOOSE_PREFIX}"), ChatStates.choose_ticket
)
async def handle_choose_ticket(
    event: MessageCallback, context: BaseContext, db: AsyncSession, user: User
) -> None:
    ticket_id = parse_id(event.callback.payload, CHAT_CHOOSE_PREFIX)
    if ticket_id is None:
        await event.ack(notification=OUTDATED_BUTTON_TEXT)
        return
    data = await context.get_data()
    try:
        await _message_service(db).add_client_message(
            user,
            ticket_id,
            text=data.get("text") or None,
            file_ids=list(data.get("file_ids", [])),
            max_message_id=data.get("max_message_id"),
        )
    except AppException as exc:
        await context.clear()
        await _edit(event, exc.message)
        return
    ticket = await _client_service(db).get_ticket(user, ticket_id)
    await context.clear()
    await _edit(event, CHAT_SENT.format(label=ticket_dative(ticket.type, ticket.id)))


@router.message_callback(
    F.callback.payload == CHAT_QUESTION,
    ChatStates.choose_ticket,
    ChatStates.confirm_question,
)
async def handle_question(
    event: MessageCallback, context: BaseContext, db: AsyncSession, user: User
) -> None:
    data = await context.get_data()
    try:
        ticket = await _client_service(db).create_question(
            user,
            description=data.get("text", ""),
            photo_ids=list(data.get("file_ids", [])),
        )
    except AppException as exc:
        await context.clear()
        await _edit(event, exc.message)
        return
    await context.clear()
    await _edit(event, QUESTION_SENT.format(ticket_id=ticket.id))


@router.message_callback(
    F.callback.payload == CHAT_CANCEL,
    ChatStates.choose_ticket,
    ChatStates.confirm_question,
)
async def handle_cancel(event: MessageCallback, context: BaseContext) -> None:
    await context.clear()
    await _edit(event, CHAT_NOT_SENT)


@router.message_callback(F.callback.payload.regexp(rf"^{CHAT_TICKET_PREFIX}"), None)
async def handle_reply_button(
    event: MessageCallback, context: BaseContext, db: AsyncSession, user: User
) -> None:
    ticket_id = parse_id(event.callback.payload, CHAT_TICKET_PREFIX)
    if ticket_id is None:
        await event.ack(notification=OUTDATED_BUTTON_TEXT)
        return
    try:
        ticket = await _client_service(db).set_active_ticket(user, ticket_id)
    except AppException as exc:
        await event.ack(notification=exc.message)
        return
    await event.ack(notification=CHAT_WRITE_NOTIFICATION)
    await event.send(CHAT_WRITE_PROMPT.format(label=ticket_dative(ticket.type, ticket.id)))


@router.message_callback(F.callback.payload.regexp(rf"^{CHAT_TICKET_PREFIX}"))
async def handle_reply_button_in_state(
    event: MessageCallback, context: BaseContext, db: AsyncSession, user: User
) -> None:
    await event.ack(notification=CHAT_FINISH_CURRENT)


@router.message_callback(F.callback.payload.regexp(rf"^{CHAT_PREFIX}"))
async def handle_stale_callback(event: MessageCallback) -> None:
    await event.ack(notification=OUTDATED_BUTTON_TEXT)
