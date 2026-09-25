import mimetypes
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import AppException, NotFoundException
from src.models.file import File
from src.providers.storage_provider import StorageProvider
from src.repositories.file_repository import FileRepository

MAX_FILE_SIZE = 20 * 1024 * 1024


class FileService:
    def __init__(self, db: AsyncSession, storage: StorageProvider):
        self.db = db
        self.storage = storage
        self.files = FileRepository(db)

    async def save(
        self,
        data: bytes,
        mime: str,
        original_name: str | None = None,
        ticket_id: int | None = None,
        message_id: int | None = None,
    ) -> File:
        if not data:
            raise AppException("Файл пуст", status_code=400)
        if len(data) > MAX_FILE_SIZE:
            raise AppException("Файл слишком большой", status_code=413)

        now = datetime.now(UTC)
        extension = mimetypes.guess_extension(mime) or ""
        key = f"files/{now:%Y}/{now:%m}/{uuid4().hex}{extension}"

        await self.storage.save(key, data)
        try:
            file = await self.files.create(
                storage_key=key,
                mime=mime,
                size=len(data),
                original_name=original_name,
                ticket_id=ticket_id,
                message_id=message_id,
            )
            await self.db.commit()
        except Exception:
            await self.storage.delete(key)
            raise
        return file

    async def read(self, file_id: int) -> tuple[File, bytes]:
        file = await self.files.get_by_id(file_id)
        if file is None:
            raise NotFoundException("Файл не найден")
        try:
            data = await self.storage.read(file.storage_key)
        except FileNotFoundError:
            raise NotFoundException("Файл не найден")
        return file, data
