from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.repositories.ticket_repository import TicketRepository
from src.schemas.dashboard import DashboardResponse
from src.services.dashboard import TicketFacts, build_dashboard, period_bounds
from src.services.ticket_rules import OPEN_STATUSES


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.tickets = TicketRepository(db)

    async def get(self, days: int) -> DashboardResponse:
        return (await self.snapshot(days))[1]

    async def snapshot(self, days: int) -> tuple[list[TicketFacts], DashboardResponse]:
        tz = ZoneInfo(settings.timezone)
        now = datetime.now(UTC)
        bounds = period_bounds(now, days, tz)
        rows = await self.tickets.list_for_dashboard(
            since=bounds.previous_start,
            open_statuses=OPEN_STATUSES,
        )
        facts = [TicketFacts(**row._mapping) for row in rows]
        dashboard = build_dashboard(
            facts,
            now=now,
            days=days,
            tz=tz,
            reaction=timedelta(hours=settings.sla_reaction_hours),
            resolution=timedelta(hours=settings.sla_resolution_hours),
        )
        return facts, dashboard
