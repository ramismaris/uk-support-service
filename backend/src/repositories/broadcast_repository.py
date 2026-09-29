from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import BroadcastStatus
from src.models.broadcast import Broadcast
from src.models.building import Building


class BroadcastRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        author_id: int,
        text: str,
        file_id: int | None,
        recipients_total: int,
        buildings: list[Building],
        status: BroadcastStatus = BroadcastStatus.SENDING,
    ) -> Broadcast:
        broadcast = Broadcast(
            author_id=author_id,
            text=text,
            file_id=file_id,
            status=status,
            recipients_total=recipients_total,
            delivered_count=0,
            failed_count=0,
        )
        broadcast.buildings = buildings
        self.db.add(broadcast)
        await self.db.flush()
        return broadcast

    async def get_by_id(self, broadcast_id: int) -> Broadcast | None:
        result = await self.db.execute(select(Broadcast).where(Broadcast.id == broadcast_id))
        return result.scalar_one_or_none()

    async def list(self, *, skip: int = 0, limit: int = 50) -> list[Broadcast]:
        result = await self.db.execute(
            select(Broadcast).order_by(Broadcast.id.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        result = await self.db.execute(select(func.count()).select_from(Broadcast))
        return result.scalar_one()

    async def save_progress(
        self, broadcast_id: int, *, delivered_count: int, failed_count: int
    ) -> None:
        await self.db.execute(
            update(Broadcast)
            .where(Broadcast.id == broadcast_id)
            .values(delivered_count=delivered_count, failed_count=failed_count)
        )

    async def finish(self, broadcast_id: int, status: BroadcastStatus) -> None:
        await self.db.execute(
            update(Broadcast)
            .where(Broadcast.id == broadcast_id)
            .values(status=status, finished_at=func.now())
        )

    async def interrupt_sending(self) -> int:
        result = await self.db.execute(
            update(Broadcast)
            .where(Broadcast.status == BroadcastStatus.SENDING)
            .values(status=BroadcastStatus.INTERRUPTED, finished_at=func.now())
        )
        return result.rowcount
