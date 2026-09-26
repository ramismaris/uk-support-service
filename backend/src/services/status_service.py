import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.background import run_in_background
from src.core.constants import TicketStatus, UserRole
from src.core.exceptions import (
    AppException,
    ConflictException,
    MessengerException,
    NotFoundException,
)
from src.core.texts import (
    RATING_INVALID,
    RATING_ONLY_CLOSED,
    REJECT_REASON_REQUIRED,
    STATUS_COMMENT_LIMIT,
    STATUS_COMMENT_TOO_LONG,
    TICKET_NOT_FOUND,
)
from src.models.ticket import Ticket
from src.models.user import User
from src.providers.messenger_provider import MessengerProvider
from src.repositories.status_change_repository import StatusChangeRepository
from src.repositories.ticket_repository import TicketRepository
from src.services import ticket_rules
from src.services.events import publish_ticket_updated
from src.services.notification_service import (
    NotificationService,
    notify_staff_about_reopened_ticket,
)

logger = logging.getLogger(__name__)


class StatusService:
    def __init__(self, db: AsyncSession, messenger: MessengerProvider):
        self.db = db
        self.messenger = messenger
        self.tickets = TicketRepository(db)
        self.status_changes = StatusChangeRepository(db)
        self.notifications = NotificationService(db, messenger)

    async def change_by_staff(
        self,
        ticket_id: int,
        staff: User,
        target: TicketStatus,
        comment: str | None,
    ) -> Ticket:
        comment = comment.strip() if comment is not None else None
        comment = comment or None
        if comment is not None and len(comment) > STATUS_COMMENT_LIMIT:
            raise AppException(STATUS_COMMENT_TOO_LONG, status_code=400)
        if target == TicketStatus.REJECTED and comment is None:
            raise AppException(REJECT_REASON_REQUIRED, status_code=400)

        ticket = await self.tickets.get_by_id_for_update(ticket_id)
        if ticket is None:
            raise NotFoundException(TICKET_NOT_FOUND)

        now = datetime.now(UTC)
        ticket_rules.check_transition(
            ticket.status, target, staff.role, closed_at=ticket.closed_at, now=now
        )

        await self._apply_transition(
            ticket,
            target,
            changed_by_id=staff.id,
            comment=comment,
            now=now,
            assignee_id=staff.id,
        )
        await self.db.commit()

        try:
            await self.notifications.send_status_message(ticket, comment)
        except MessengerException:
            logger.warning("Failed to send status message for ticket %s", ticket.id)

        await publish_ticket_updated(self.db, ticket.id)
        return await self.tickets.get_by_id(ticket_id, populate_existing=True)

    async def reopen_by_client(self, client: User, ticket_id: int) -> Ticket:
        ticket = await self.tickets.get_by_id_for_update(ticket_id)
        if ticket is None or ticket.client_id != client.id:
            raise NotFoundException(TICKET_NOT_FOUND)

        now = datetime.now(UTC)
        ticket_rules.check_transition(
            ticket.status,
            TicketStatus.IN_PROGRESS,
            UserRole.CLIENT,
            closed_at=ticket.closed_at,
            now=now,
        )

        await self._apply_transition(
            ticket,
            TicketStatus.IN_PROGRESS,
            changed_by_id=client.id,
            comment=None,
            now=now,
        )
        await self.db.commit()

        try:
            await self.notifications.update_status_card(ticket)
        except MessengerException:
            logger.warning("Failed to update status card for ticket %s", ticket.id)

        run_in_background(
            notify_staff_about_reopened_ticket(ticket.id),
            name=f"notify-reopened-{ticket.id}",
        )

        await publish_ticket_updated(self.db, ticket.id)
        return await self.tickets.get_by_id(ticket_id, populate_existing=True)

    async def rate(self, client: User, ticket_id: int, score: int) -> Ticket:
        if score < 1 or score > 5:
            raise AppException(RATING_INVALID, status_code=400)

        ticket = await self.tickets.get_by_id(ticket_id)
        if ticket is None or ticket.client_id != client.id:
            raise NotFoundException(TICKET_NOT_FOUND)
        if not ticket_rules.can_rate(ticket.status):
            raise ConflictException(RATING_ONLY_CLOSED)

        ticket.rating = score
        await self.db.commit()
        await publish_ticket_updated(self.db, ticket.id)
        return ticket

    async def _apply_transition(
        self,
        ticket: Ticket,
        target: TicketStatus,
        *,
        changed_by_id: int | None,
        comment: str | None,
        now: datetime,
        assignee_id: int | None = None,
    ) -> None:
        from_status = ticket.status
        await self.status_changes.create(
            ticket.id,
            from_status,
            target,
            changed_by_id=changed_by_id,
            comment=comment,
        )

        if from_status == TicketStatus.NEW and target == TicketStatus.IN_PROGRESS:
            ticket.assignee_id = assignee_id
        if target in (TicketStatus.CLOSED, TicketStatus.REJECTED):
            ticket.closed_at = now
        elif target == TicketStatus.IN_PROGRESS and from_status in (
            TicketStatus.CLOSED,
            TicketStatus.REJECTED,
        ):
            ticket.closed_at = None
        ticket.status = target
