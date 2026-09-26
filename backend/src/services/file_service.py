import mimetypes
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import AppException, NotFoundException
from src.core.texts import (
    CONTENT_IMAGE_FORMAT,
    PHOTO_ALREADY_ATTACHED,
    PHOTO_NOT_FOUND,
    PHOTOS_DUPLICATED,
)
from src.models.file import File
from src.providers.storage_provider import StorageProvider
from src.repositories.file_repository import FileRepository

MAX_FILE_SIZE = 20 * 1024 * 1024

CONTENT_IMAGE_MIMES = frozenset({"image/png", "image/jpeg"})

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_JPEG_SIGNATURE = b"\xff\xd8\xff"


def _image_mime(data: bytes) -> str:
    if data.startswith(_PNG_SIGNATURE):
        return "image/png"
    if data.startswith(_JPEG_SIGNATURE):
        return "image/jpeg"
    raise AppException(CONTENT_IMAGE_FORMAT, status_code=400)


class FileService:
    def __init__(self, db: AsyncSession, storage: StorageProvider):
        self.db = db
        self.storage = storage
        self.files = FileRepository(db)

    def check_data(self, data: bytes) -> None:
        if not data:
            raise AppException("Файл пуст", status_code=400)
        if len(data) > MAX_FILE_SIZE:
            raise AppException("Файл слишком большой", status_code=413)

    async def get_unattached(self, file_ids: list[int]) -> list[File]:
        if len(set(file_ids)) != len(file_ids):
            raise AppException(PHOTOS_DUPLICATED, status_code=400)

        files = await self.files.list_by_ids(file_ids)
        files_by_id = {file.id: file for file in files}
        for file_id in file_ids:
            file = files_by_id.get(file_id)
            if file is None:
                raise AppException(PHOTO_NOT_FOUND, status_code=400)
            if file.ticket_id is not None or file.message_id is not None:
                raise AppException(PHOTO_ALREADY_ATTACHED, status_code=400)
        return files

    async def add(
        self,
        data: bytes,
        mime: str,
        original_name: str | None = None,
        *,
        ticket_id: int | None = None,
        message_id: int | None = None,
    ) -> File:
        self.check_data(data)

        if original_name is not None:
            original_name = original_name.replace("\x00", "") or None

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
            await self.db.flush()
        except Exception:
            await self.storage.delete(key)
            raise
        return file

    async def save(
        self,
        data: bytes,
        mime: str,
        original_name: str | None = None,
        ticket_id: int | None = None,
        message_id: int | None = None,
    ) -> File:
        file = await self.add(
            data,
            mime,
            original_name,
            ticket_id=ticket_id,
            message_id=message_id,
        )
        try:
            await self.db.commit()
        except Exception:
            await self.storage.delete(file.storage_key)
            raise
        return file

    async def save_image(self, data: bytes, original_name: str | None) -> File:
        self.check_data(data)
        mime = _image_mime(data)
        return await self.save(data, mime, original_name)

    async def read(self, file_id: int) -> tuple[File, bytes]:
        file = await self.files.get_by_id(file_id)
        if file is None:
            raise NotFoundException("Файл не найден")
        try:
            data = await self.storage.read(file.storage_key)
        except FileNotFoundError:
            raise NotFoundException("Файл не найден")
        return file, data
