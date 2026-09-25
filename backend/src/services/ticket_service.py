from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import TicketStatus
from src.core.exceptions import NotFoundException
from src.models.file import File
from src.models.status_change import StatusChange
from src.models.ticket import Ticket
from src.models.user import User
from src.repositories.file_repository import FileRepository
from src.repositories.status_change_repository import StatusChangeRepository
from src.repositories.ticket_repository import TicketRepository
from src.services import ticket_rules


class TicketService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.tickets = TicketRepository(db)
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
            raise NotFoundException("Обращение не найдено")
        files = await self.files.list_by_ticket(ticket_id)
        history = await self.status_changes.list_by_ticket(ticket_id)
        return ticket, files, history
