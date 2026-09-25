from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import TicketStatus
from src.models.status_change import StatusChange


class StatusChangeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        ticket_id: int,
        from_status: TicketStatus | None,
        to_status: TicketStatus,
        changed_by_id: int | None = None,
        comment: str | None = None,
        created_at: datetime | None = None,
    ) -> StatusChange:
        change = StatusChange(
            ticket_id=ticket_id,
            from_status=from_status,
            to_status=to_status,
            changed_by_id=changed_by_id,
            comment=comment,
        )
        if created_at is not None:
            change.created_at = created_at
        self.db.add(change)
        await self.db.flush()
        return change

    async def list_by_ticket(self, ticket_id: int) -> list[StatusChange]:
        result = await self.db.execute(
            select(StatusChange)
            .where(StatusChange.ticket_id == ticket_id)
            .order_by(StatusChange.created_at, StatusChange.id)
        )
        return list(result.scalars().all())
