from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.file import File


class FileRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        storage_key: str,
        mime: str,
        size: int,
        original_name: str | None = None,
        ticket_id: int | None = None,
        message_id: int | None = None,
    ) -> File:
        file = File(
            storage_key=storage_key,
            mime=mime,
            size=size,
            original_name=original_name,
            ticket_id=ticket_id,
            message_id=message_id,
        )
        self.db.add(file)
        await self.db.flush()
        return file

    async def get_by_id(self, file_id: int) -> File | None:
        result = await self.db.execute(select(File).where(File.id == file_id))
        return result.scalar_one_or_none()

    async def list_by_ticket(self, ticket_id: int) -> list[File]:
        result = await self.db.execute(
            select(File)
            .where(File.ticket_id == ticket_id, File.message_id.is_(None))
            .order_by(File.id)
        )
        return list(result.scalars().all())
