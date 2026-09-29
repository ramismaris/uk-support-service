from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.category_repository import CategoryRepository


async def test_get_by_title_returns_category(db: AsyncSession) -> None:
    repository = CategoryRepository(db)
    created = await repository.create("Сантехника", 1)

    found = await repository.get_by_title("Сантехника")

    assert found is not None
    assert found.id == created.id


async def test_list_all_orders_by_sort_order_then_id(db: AsyncSession) -> None:
    repository = CategoryRepository(db)
    # Created out of order; the result must follow sort_order, not the id.
    third = await repository.create("Другое", 3)
    first = await repository.create("Сантехника", 1)
    second = await repository.create("Электрика", 2)
    tie = await repository.create("Тот же порядок", 1)

    categories = await repository.list_all()

    assert [category.id for category in categories] == [first.id, tie.id, second.id, third.id]


async def test_count_active_ignores_inactive(db: AsyncSession) -> None:
    repository = CategoryRepository(db)
    await repository.create("Сантехника", 1)
    await repository.create("Электрика", 2)
    inactive = await repository.create("Другое", 3)
    inactive.is_active = False
    await db.flush()

    assert await repository.count_active() == 2


async def test_max_sort_order_is_zero_on_empty_table(db: AsyncSession) -> None:
    assert await CategoryRepository(db).max_sort_order() == 0


async def test_max_sort_order_returns_maximum(db: AsyncSession) -> None:
    repository = CategoryRepository(db)
    await repository.create("Сантехника", 1)
    await repository.create("Электрика", 7)

    assert await repository.max_sort_order() == 7


async def test_list_active_orders_by_sort_order(db: AsyncSession) -> None:
    repository = CategoryRepository(db)
    await repository.create("Электрика", 2)
    await repository.create("Сантехника", 1)
    inactive = await repository.create("Другое", 3)
    inactive.is_active = False
    await db.flush()

    categories = await repository.list_active()

    assert [category.title for category in categories] == ["Сантехника", "Электрика"]
