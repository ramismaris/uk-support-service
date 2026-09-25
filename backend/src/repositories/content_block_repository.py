from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import ContentKey
from src.models.content_block import ContentBlock


class ContentBlockRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, key: ContentKey) -> ContentBlock | None:
        result = await self.db.execute(select(ContentBlock).where(ContentBlock.key == key))
        return result.scalar_one_or_none()

    async def list_all(self) -> list[ContentBlock]:
        result = await self.db.execute(select(ContentBlock).order_by(ContentBlock.key))
        return list(result.scalars().all())

    async def create(
        self,
        key: ContentKey,
        data: dict,
        updated_by_id: int | None = None,
    ) -> ContentBlock:
        block = ContentBlock(key=key, data=data, updated_by_id=updated_by_id)
        self.db.add(block)
        await self.db.flush()
        return block
