from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import DIRECTORY_ACTIVE_LIMIT
from src.core.exceptions import ConflictException, NotFoundException
from src.core.texts import (
    CATEGORIES_LIMIT,
    CATEGORY_EXISTS,
    CATEGORY_LAST_ACTIVE,
    CATEGORY_NOT_FOUND,
    CATEGORY_ORDER_STALE,
)
from src.models.category import Category
from src.repositories.category_repository import CategoryRepository


class CategoryService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.categories = CategoryRepository(db)

    async def list_active(self) -> list[Category]:
        return await self.categories.list_active()

    async def list_all(self) -> list[Category]:
        return await self.categories.list_all()

    async def create(self, title: str) -> Category:
        if await self.categories.count_active() >= DIRECTORY_ACTIVE_LIMIT:
            raise ConflictException(CATEGORIES_LIMIT)

        try:
            category = await self.categories.create(
                title, await self.categories.max_sort_order() + 1
            )
        except IntegrityError:
            await self.db.rollback()
            raise ConflictException(CATEGORY_EXISTS)

        await self.db.commit()
        return category

    async def update(
        self,
        category_id: int,
        *,
        title: str | None,
        is_active: bool | None,
    ) -> Category:
        category = await self.categories.get_by_id(category_id)
        if category is None:
            raise NotFoundException(CATEGORY_NOT_FOUND)

        # All checks before any attribute is changed: autoflush would otherwise persist a
        # half-changed row and a count would already include it.
        if (
            is_active is True
            and not category.is_active
            and await self.categories.count_active() >= DIRECTORY_ACTIVE_LIMIT
        ):
            raise ConflictException(CATEGORIES_LIMIT)
        if is_active is False and category.is_active and await self.categories.count_active() <= 1:
            raise ConflictException(CATEGORY_LAST_ACTIVE)

        if title is not None:
            category.title = title
        if is_active is not None:
            category.is_active = is_active

        try:
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            raise ConflictException(CATEGORY_EXISTS)

        await self.db.commit()
        return category

    async def reorder(self, ids: list[int]) -> list[Category]:
        categories = await self.categories.list_all()
        if len(ids) != len(categories) or set(ids) != {category.id for category in categories}:
            raise ConflictException(CATEGORY_ORDER_STALE)

        by_id = {category.id: category for category in categories}
        for position, category_id in enumerate(ids, start=1):
            by_id[category_id].sort_order = position

        await self.db.commit()
        return await self.categories.list_all()
