from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.residence import Residence


class ResidenceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        user_id: int,
        building_id: int,
        apartment: str,
        is_primary: bool = False,
    ) -> Residence:
        residence = Residence(
            user_id=user_id,
            building_id=building_id,
            apartment=apartment,
            is_primary=is_primary,
        )
        self.db.add(residence)
        await self.db.flush()
        return residence

    async def get(self, user_id: int, building_id: int, apartment: str) -> Residence | None:
        result = await self.db.execute(
            select(Residence).where(
                Residence.user_id == user_id,
                Residence.building_id == building_id,
                Residence.apartment == apartment,
            )
        )
        return result.scalar_one_or_none()
