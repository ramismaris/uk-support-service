from collections.abc import Iterable, Sequence
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import TicketPriority, TicketStatus, TicketType
from src.models.building import Building
from src.models.category import Category
from src.models.status_change import StatusChange
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

    async def count_unread(self, *, statuses: Iterable[TicketStatus]) -> int:
        # Same rule as ticket_rules.is_unread, in SQL.
        query = select(func.count()).where(
            Ticket.status.in_(statuses),
            Ticket.last_client_message_at.is_not(None),
            or_(
                Ticket.staff_seen_at.is_(None),
                Ticket.last_client_message_at > Ticket.staff_seen_at,
            ),
        )
        result = await self.db.execute(query)
        return result.scalar_one()

    async def list_for_dashboard(
        self,
        *,
        since: datetime,
        open_statuses: Iterable[TicketStatus],
    ) -> Sequence[Row]:
        # reacted_at: the single change out of NEW (taken, first reply or rejection).
        reacted_at = (
            select(func.min(StatusChange.created_at))
            .where(
                StatusChange.ticket_id == Ticket.id,
                StatusChange.from_status == TicketStatus.NEW,
            )
            .scalar_subquery()
            .label("reacted_at")
        )
        query = (
            select(
                Ticket.type.label("type"),
                Ticket.status.label("status"),
                Ticket.category_id.label("category_id"),
                Category.title.label("category_title"),
                Category.sort_order.label("category_sort_order"),
                Ticket.created_at.label("created_at"),
                Ticket.closed_at.label("closed_at"),
                reacted_at,
                Ticket.rating.label("rating"),
                Ticket.building_id.label("building_id"),
                Building.address.label("building_address"),
                Ticket.assignee_id.label("assignee_id"),
            )
            .select_from(Ticket)
            .outerjoin(Category, Category.id == Ticket.category_id)
            .outerjoin(Building, Building.id == Ticket.building_id)
            .where(
                or_(
                    Ticket.created_at >= since,
                    Ticket.closed_at >= since,
                    Ticket.status.in_(open_statuses),
                )
            )
        )
        result = await self.db.execute(query)
        return list(result.all())

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
