from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.building import Building


class BuildingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, building_id: int) -> Building | None:
        result = await self.db.execute(select(Building).where(Building.id == building_id))
        return result.scalar_one_or_none()

    async def get_by_address(self, address: str) -> Building | None:
        result = await self.db.execute(select(Building).where(Building.address == address))
        return result.scalar_one_or_none()

    async def list_active(self) -> list[Building]:
        result = await self.db.execute(
            select(Building).where(Building.is_active.is_(True)).order_by(Building.address)
        )
        return list(result.scalars().all())

    async def create(self, address: str, external_id: str | None = None) -> Building:
        building = Building(address=address, external_id=external_id)
        self.db.add(building)
        await self.db.flush()
        return building
