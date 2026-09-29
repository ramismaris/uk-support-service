from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import DIRECTORY_ACTIVE_LIMIT
from src.core.exceptions import ConflictException, NotFoundException
from src.core.texts import (
    BUILDING_EXISTS,
    BUILDING_LAST_ACTIVE,
    BUILDING_NOT_FOUND,
    BUILDINGS_LIMIT,
)
from src.models.building import Building
from src.repositories.building_repository import BuildingRepository


class BuildingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.buildings = BuildingRepository(db)

    async def list_active(self) -> list[Building]:
        return await self.buildings.list_active()

    async def list_all(self) -> list[Building]:
        return await self.buildings.list_all()

    async def create(self, address: str) -> Building:
        if await self.buildings.count_active() >= DIRECTORY_ACTIVE_LIMIT:
            raise ConflictException(BUILDINGS_LIMIT)

        try:
            building = await self.buildings.create(address)
        except IntegrityError:
            await self.db.rollback()
            raise ConflictException(BUILDING_EXISTS)

        await self.db.commit()
        return building

    async def update(
        self,
        building_id: int,
        *,
        address: str | None,
        is_active: bool | None,
    ) -> Building:
        building = await self.buildings.get_by_id(building_id)
        if building is None:
            raise NotFoundException(BUILDING_NOT_FOUND)

        # All checks before any attribute is changed: autoflush would otherwise persist a
        # half-changed row and a count would already include it.
        if (
            is_active is True
            and not building.is_active
            and await self.buildings.count_active() >= DIRECTORY_ACTIVE_LIMIT
        ):
            raise ConflictException(BUILDINGS_LIMIT)
        if is_active is False and building.is_active and await self.buildings.count_active() <= 1:
            raise ConflictException(BUILDING_LAST_ACTIVE)

        if address is not None:
            building.address = address
        if is_active is not None:
            building.is_active = is_active

        try:
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            raise ConflictException(BUILDING_EXISTS)

        await self.db.commit()
        return building
