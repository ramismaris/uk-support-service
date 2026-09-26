import logging
from typing import TypeVar

from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import ContentKey
from src.core.exceptions import AppException
from src.core.texts import CONTENT_IMAGE_NOT_FOUND
from src.models.user import User
from src.repositories.content_block_repository import ContentBlockRepository
from src.repositories.file_repository import FileRepository
from src.schemas.content import (
    ContactsContent,
    EmergencyContent,
    PaymentContent,
    ServicesContent,
    ThemeContent,
    WelcomeContent,
)
from src.services.file_service import CONTENT_IMAGE_MIMES

logger = logging.getLogger(__name__)

ModelT = TypeVar("ModelT", bound=BaseModel)


class ContentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.blocks = ContentBlockRepository(db)
        self.files = FileRepository(db)

    async def get_welcome(self) -> WelcomeContent | None:
        return await self._get(ContentKey.WELCOME, WelcomeContent)

    async def get_emergency(self) -> EmergencyContent | None:
        return await self._get(ContentKey.EMERGENCY, EmergencyContent)

    async def get_services(self) -> ServicesContent | None:
        return await self._get(ContentKey.SERVICES, ServicesContent)

    async def get_payment(self) -> PaymentContent | None:
        return await self._get(ContentKey.PAYMENT, PaymentContent)

    async def get_contacts(self) -> ContactsContent | None:
        return await self._get(ContentKey.CONTACTS, ContactsContent)

    async def get_theme(self) -> ThemeContent | None:
        return await self._get(ContentKey.THEME, ThemeContent)

    async def save(self, key: ContentKey, content: BaseModel, admin: User) -> None:
        file_id = _file_reference(content)
        if file_id is not None:
            await self._ensure_content_image(file_id)
        await self.blocks.upsert(key, content.model_dump(mode="json"), updated_by_id=admin.id)
        await self.db.commit()

    async def _ensure_content_image(self, file_id: int) -> None:
        file = await self.files.get_by_id(file_id)
        if (
            file is None
            or file.ticket_id is not None
            or file.message_id is not None
            or file.mime not in CONTENT_IMAGE_MIMES
        ):
            raise AppException(CONTENT_IMAGE_NOT_FOUND, status_code=400)

    async def _get(self, key: ContentKey, model: type[ModelT]) -> ModelT | None:
        block = await self.blocks.get(key)
        if block is None:
            return None
        try:
            return model.model_validate(block.data)
        except ValidationError as exc:
            logger.error("Content block %s is invalid (%s): %s", key, type(exc).__name__, exc)
            return None


def _file_reference(content: BaseModel) -> int | None:
    if isinstance(content, WelcomeContent):
        return content.file_id
    if isinstance(content, ThemeContent):
        return content.logo_file_id
    return None
