from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.category import Category


class CategoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, category_id: int) -> Category | None:
        result = await self.db.execute(select(Category).where(Category.id == category_id))
        return result.scalar_one_or_none()

    async def get_by_title(self, title: str) -> Category | None:
        result = await self.db.execute(select(Category).where(Category.title == title))
        return result.scalar_one_or_none()

    async def list_active(self) -> list[Category]:
        result = await self.db.execute(
            select(Category).where(Category.is_active.is_(True)).order_by(Category.sort_order)
        )
        return list(result.scalars().all())

    async def create(self, title: str, sort_order: int) -> Category:
        category = Category(title=title, sort_order=sort_order)
        self.db.add(category)
        await self.db.flush()
        return category
