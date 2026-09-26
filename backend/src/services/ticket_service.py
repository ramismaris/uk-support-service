from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import TicketStatus
from src.core.exceptions import NotFoundException
from src.core.texts import TICKET_NOT_FOUND
from src.models.file import File
from src.models.message import Message
from src.models.status_change import StatusChange
from src.models.ticket import Ticket
from src.models.user import User
from src.repositories.file_repository import FileRepository
from src.repositories.message_repository import MessageRepository
from src.repositories.status_change_repository import StatusChangeRepository
from src.repositories.ticket_repository import TicketRepository
from src.services import ticket_rules
from src.services.events import publish_ticket_updated


class TicketService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.tickets = TicketRepository(db)
        self.messages = MessageRepository(db)
        self.files = FileRepository(db)
        self.status_changes = StatusChangeRepository(db)

    async def list_for_staff(
        self,
        staff: User,
        *,
        status: TicketStatus | None,
        building_id: int | None,
        category_id: int | None,
        mine: bool,
        skip: int,
        limit: int,
    ) -> tuple[list[Ticket], int]:
        statuses = [status] if status is not None else ticket_rules.OPEN_STATUSES
        assignee_id = staff.id if mine else None
        tickets = await self.tickets.list(
            statuses=statuses,
            building_id=building_id,
            category_id=category_id,
            assignee_id=assignee_id,
            skip=skip,
            limit=limit,
        )
        total = await self.tickets.count(
            statuses=statuses,
            building_id=building_id,
            category_id=category_id,
            assignee_id=assignee_id,
        )
        return tickets, total

    async def get_for_staff(self, ticket_id: int) -> tuple[Ticket, list[File], list[StatusChange]]:
        ticket = await self.tickets.get_by_id(ticket_id)
        if ticket is None:
            raise NotFoundException(TICKET_NOT_FOUND)
        files = await self.files.list_by_ticket(ticket_id)
        history = await self.status_changes.list_by_ticket(ticket_id)
        return ticket, files, history

    def allowed_statuses(self, ticket: Ticket, staff: User) -> list[TicketStatus]:
        return ticket_rules.allowed_statuses(
            ticket.status,
            staff.role,
            closed_at=ticket.closed_at,
            now=datetime.now(UTC),
        )

    async def list_messages(self, ticket_id: int) -> list[Message]:
        ticket = await self.tickets.get_by_id(ticket_id)
        if ticket is None:
            raise NotFoundException(TICKET_NOT_FOUND)
        return await self.messages.list_by_ticket(ticket_id)

    async def mark_read(self, ticket_id: int) -> None:
        ticket = await self.tickets.get_by_id(ticket_id)
        if ticket is None:
            raise NotFoundException(TICKET_NOT_FOUND)
        ticket.staff_seen_at = datetime.now(UTC)
        await self.db.commit()

        await publish_ticket_updated(self.db, ticket.id)
