from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.category_repository import CategoryRepository


async def test_get_by_title_returns_category(db: AsyncSession) -> None:
    repository = CategoryRepository(db)
    created = await repository.create("Сантехника", 1)

    found = await repository.get_by_title("Сантехника")

    assert found is not None
    assert found.id == created.id


async def test_list_active_orders_by_sort_order(db: AsyncSession) -> None:
    repository = CategoryRepository(db)
    await repository.create("Электрика", 2)
    await repository.create("Сантехника", 1)
    inactive = await repository.create("Другое", 3)
    inactive.is_active = False
    await db.flush()

    categories = await repository.list_active()

    assert [category.title for category in categories] == ["Сантехника", "Электрика"]
