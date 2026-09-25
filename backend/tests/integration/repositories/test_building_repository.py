from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.building_repository import BuildingRepository


async def test_get_by_address_returns_building(db: AsyncSession) -> None:
    repository = BuildingRepository(db)
    created = await repository.create("ул. Ленина, 12", external_id="UK-001")

    found = await repository.get_by_address("ул. Ленина, 12")

    assert found is not None
    assert found.id == created.id


async def test_get_by_address_returns_none_when_missing(db: AsyncSession) -> None:
    repository = BuildingRepository(db)

    assert await repository.get_by_address("ул. Неизвестная, 1") is None


async def test_list_active_excludes_inactive_and_orders_by_address(db: AsyncSession) -> None:
    repository = BuildingRepository(db)
    await repository.create("ул. Б, 1")
    await repository.create("ул. А, 1")
    inactive = await repository.create("ул. В, 1")
    inactive.is_active = False
    await db.flush()

    buildings = await repository.list_active()

    assert [building.address for building in buildings] == ["ул. А, 1", "ул. Б, 1"]
