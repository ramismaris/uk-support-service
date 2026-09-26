import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.background import run_in_background
from src.core.ws_manager import ws_manager
from src.repositories.message_repository import MessageRepository
from src.repositories.ticket_repository import TicketRepository
from src.schemas.message import MessageResponse
from src.schemas.ticket import TicketListItemResponse

logger = logging.getLogger(__name__)


async def publish_ticket_created(db: AsyncSession, ticket_id: int) -> None:
    await _publish_ticket(
        db,
        ticket_id,
        event_type="ticket_created",
        name=f"ws-ticket-created-{ticket_id}",
    )


async def publish_ticket_updated(db: AsyncSession, ticket_id: int) -> None:
    await _publish_ticket(
        db,
        ticket_id,
        event_type="ticket_updated",
        name=f"ws-ticket-updated-{ticket_id}",
    )


async def publish_message_created(db: AsyncSession, message_id: int) -> None:
    try:
        message = await MessageRepository(db).get_by_id(message_id, populate_existing=True)
        if message is None:
            logger.warning("Cannot publish message_created: message %s not found", message_id)
            return
        payload = {
            "type": "message_created",
            "message": MessageResponse.model_validate(message).model_dump(mode="json"),
        }
    except Exception:
        logger.exception("Failed to build message_created payload for message %s", message_id)
        return
    run_in_background(ws_manager.broadcast(payload), name=f"ws-message-created-{message_id}")


async def _publish_ticket(db: AsyncSession, ticket_id: int, *, event_type: str, name: str) -> None:
    try:
        ticket = await TicketRepository(db).get_by_id(ticket_id, populate_existing=True)
        if ticket is None:
            logger.warning("Cannot publish %s: ticket %s not found", event_type, ticket_id)
            return
        payload = {
            "type": event_type,
            "ticket": TicketListItemResponse.model_validate(ticket).model_dump(mode="json"),
        }
    except Exception:
        logger.exception("Failed to build %s payload for ticket %s", event_type, ticket_id)
        return
    run_in_background(ws_manager.broadcast(payload), name=name)
