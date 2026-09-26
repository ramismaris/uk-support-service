from maxapi import Router
from maxapi.filters import F
from maxapi.types import MessageCallback
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards import RATE_PREFIX, main_menu_keyboard, rating_keyboard
from src.bot.utils import parse_id
from src.core.constants import RESOLVED_NO_PREFIX, RESOLVED_YES_PREFIX
from src.core.exceptions import AppException
from src.core.texts import (
    OUTDATED_BUTTON_TEXT,
    RATE_PROMPT,
    RATE_THANKS,
    REOPENED_TEXT,
    ticket_dative,
    ticket_genitive,
)
from src.models.user import User
from src.providers.factory import get_messenger_provider, get_storage_provider
from src.services.client_ticket_service import ClientTicketService
from src.services.status_service import StatusService

router = Router("resolution")


def _client_service(db: AsyncSession) -> ClientTicketService:
    return ClientTicketService(db, get_messenger_provider(), get_storage_provider())


def _status_service(db: AsyncSession) -> StatusService:
    return StatusService(db, get_messenger_provider())


def _parse_score(payload: str) -> tuple[int, int] | None:
    if not payload.startswith(RATE_PREFIX):
        return None
    raw_id, separator, raw_score = payload[len(RATE_PREFIX) :].partition(":")
    if not separator:
        return None
    ticket_id = parse_id(f"{RATE_PREFIX}{raw_id}", RATE_PREFIX)
    if ticket_id is None:
        return None
    if not raw_score.isascii() or not raw_score.isdigit():
        return None
    score = int(raw_score)
    if score < 1 or score > 5:
        return None
    return ticket_id, score


async def _edit(event: MessageCallback, text: str, attachments: list | None = None) -> None:
    try:
        await event.edit(text=text, attachments=attachments or [])
    except ValueError:
        await event.ack(notification=OUTDATED_BUTTON_TEXT)


@router.message_callback(F.callback.payload.regexp(rf"^{RESOLVED_YES_PREFIX}"))
async def handle_resolved_yes(event: MessageCallback, db: AsyncSession, user: User) -> None:
    ticket_id = parse_id(event.callback.payload, RESOLVED_YES_PREFIX)
    if ticket_id is None:
        await event.ack(notification=OUTDATED_BUTTON_TEXT)
        return
    try:
        ticket = await _client_service(db).get_ticket(user, ticket_id)
    except AppException as exc:
        await event.ack(notification=exc.message)
        return
    await _edit(
        event,
        RATE_PROMPT.format(label=ticket_dative(ticket.type, ticket.id)),
        [rating_keyboard(ticket.id)],
    )


@router.message_callback(F.callback.payload.regexp(rf"^{RATE_PREFIX}"))
async def handle_rate(event: MessageCallback, db: AsyncSession, user: User) -> None:
    parsed = _parse_score(event.callback.payload)
    if parsed is None:
        await event.ack(notification=OUTDATED_BUTTON_TEXT)
        return
    ticket_id, score = parsed
    try:
        await _status_service(db).rate(user, ticket_id, score)
    except AppException as exc:
        await event.ack(notification=exc.message)
        return
    await _edit(event, RATE_THANKS)


@router.message_callback(F.callback.payload.regexp(rf"^{RESOLVED_NO_PREFIX}"))
async def handle_resolved_no(event: MessageCallback, db: AsyncSession, user: User) -> None:
    ticket_id = parse_id(event.callback.payload, RESOLVED_NO_PREFIX)
    if ticket_id is None:
        await event.ack(notification=OUTDATED_BUTTON_TEXT)
        return
    try:
        ticket = await _status_service(db).reopen_by_client(user, ticket_id)
        await _client_service(db).set_active_ticket(user, ticket_id)
    except AppException as exc:
        await _edit(event, exc.message, [main_menu_keyboard()])
        return
    await _edit(event, REOPENED_TEXT.format(label=ticket_genitive(ticket.type, ticket.id)))


@router.message_callback(F.callback.payload.regexp(r"^resolved:"))
async def handle_stale_resolution(event: MessageCallback) -> None:
    await event.ack(notification=OUTDATED_BUTTON_TEXT)
