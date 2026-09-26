from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import TicketPriority, TicketStatus, TicketType
from src.models.ticket import Ticket


class TicketRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        type: TicketType,
        status: TicketStatus,
        client_id: int,
        description: str,
        priority: TicketPriority = TicketPriority.NORMAL,
        assignee_id: int | None = None,
        category_id: int | None = None,
        building_id: int | None = None,
        apartment: str | None = None,
        contact_phone: str | None = None,
        preferred_time: str | None = None,
        rating: int | None = None,
        created_at: datetime | None = None,
        closed_at: datetime | None = None,
    ) -> Ticket:
        ticket = Ticket(
            type=type,
            status=status,
            client_id=client_id,
            description=description,
            priority=priority,
            assignee_id=assignee_id,
            category_id=category_id,
            building_id=building_id,
            apartment=apartment,
            contact_phone=contact_phone,
            preferred_time=preferred_time,
            rating=rating,
            closed_at=closed_at,
        )
        if created_at is not None:
            ticket.created_at = created_at
        self.db.add(ticket)
        await self.db.flush()
        return ticket

    async def get_by_id(self, ticket_id: int, *, populate_existing: bool = False) -> Ticket | None:
        result = await self.db.execute(
            select(Ticket)
            .where(Ticket.id == ticket_id)
            .execution_options(populate_existing=populate_existing)
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_update(self, ticket_id: int) -> Ticket | None:
        result = await self.db.execute(
            select(Ticket)
            .where(Ticket.id == ticket_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def get_by_status_message_max_id(self, max_message_id: str) -> Ticket | None:
        result = await self.db.execute(
            select(Ticket).where(Ticket.status_message_max_id == max_message_id)
        )
        return result.scalar_one_or_none()

    async def list_by_client(
        self,
        client_id: int,
        *,
        statuses: Iterable[TicketStatus],
        limit: int | None = None,
    ) -> list[Ticket]:
        query = (
            select(Ticket)
            .where(Ticket.client_id == client_id, Ticket.status.in_(statuses))
            .order_by(Ticket.created_at.desc(), Ticket.id.desc())
        )
        if limit is not None:
            query = query.limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def list(
        self,
        *,
        statuses: Iterable[TicketStatus],
        building_id: int | None = None,
        category_id: int | None = None,
        assignee_id: int | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Ticket]:
        query = self._filtered(
            statuses=statuses,
            building_id=building_id,
            category_id=category_id,
            assignee_id=assignee_id,
        )
        query = query.order_by(Ticket.created_at.desc(), Ticket.id.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count(
        self,
        *,
        statuses: Iterable[TicketStatus],
        building_id: int | None = None,
        category_id: int | None = None,
        assignee_id: int | None = None,
    ) -> int:
        query = self._filtered(
            statuses=statuses,
            building_id=building_id,
            category_id=category_id,
            assignee_id=assignee_id,
        )
        result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        return result.scalar_one()

    def _filtered(
        self,
        *,
        statuses: Iterable[TicketStatus],
        building_id: int | None,
        category_id: int | None,
        assignee_id: int | None,
    ):
        query = select(Ticket).where(Ticket.status.in_(statuses))
        if building_id is not None:
            query = query.where(Ticket.building_id == building_id)
        if category_id is not None:
            query = query.where(Ticket.category_id == category_id)
        if assignee_id is not None:
            query = query.where(Ticket.assignee_id == assignee_id)
        return query
