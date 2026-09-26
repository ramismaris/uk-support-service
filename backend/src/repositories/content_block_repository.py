from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
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

    async def upsert(
        self,
        key: ContentKey,
        data: dict,
        updated_by_id: int | None = None,
    ) -> None:
        # onupdate of the model does not run for INSERT ... ON CONFLICT, so set updated_at here.
        statement = (
            insert(ContentBlock)
            .values(key=key, data=data, updated_by_id=updated_by_id, updated_at=func.now())
            .on_conflict_do_update(
                index_elements=[ContentBlock.key],
                set_={
                    "data": data,
                    "updated_by_id": updated_by_id,
                    "updated_at": func.now(),
                },
            )
        )
        await self.db.execute(statement)
