from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.building_repository import BuildingRepository
from src.repositories.residence_repository import ResidenceRepository
from src.repositories.user_repository import UserRepository


async def test_list_by_user_returns_only_own_residences_primary_first(
    db: AsyncSession,
) -> None:
    users = UserRepository(db)
    client = await users.create(max_user_id=1, first_name="Мария")
    other = await users.create(max_user_id=2, first_name="Пётр")
    buildings = BuildingRepository(db)
    first_building = await buildings.create("ул. Ленина, 1")
    second_building = await buildings.create("ул. Ленина, 2")
    await db.commit()

    residences = ResidenceRepository(db)
    secondary = await residences.create(client.id, first_building.id, "1")
    primary = await residences.create(client.id, second_building.id, "2", is_primary=True)
    await residences.create(other.id, first_building.id, "3", is_primary=True)
    await db.commit()

    found = await residences.list_by_user(client.id)

    assert [residence.id for residence in found] == [primary.id, secondary.id]


async def test_list_by_user_returns_empty_without_residences(db: AsyncSession) -> None:
    client = await UserRepository(db).create(max_user_id=1, first_name="Мария")
    await db.commit()

    assert await ResidenceRepository(db).list_by_user(client.id) == []
