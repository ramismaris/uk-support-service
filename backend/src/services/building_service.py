from sqlalchemy.ext.asyncio import AsyncSession

from src.models.building import Building
from src.repositories.building_repository import BuildingRepository


class BuildingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.buildings = BuildingRepository(db)

    async def list_active(self) -> list[Building]:
        return await self.buildings.list_active()
