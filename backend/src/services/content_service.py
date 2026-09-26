import logging
from typing import TypeVar

from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import ContentKey
from src.repositories.content_block_repository import ContentBlockRepository
from src.schemas.content import (
    ContactsContent,
    EmergencyContent,
    PaymentContent,
    ServicesContent,
    WelcomeContent,
)

logger = logging.getLogger(__name__)

ModelT = TypeVar("ModelT", bound=BaseModel)


class ContentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.blocks = ContentBlockRepository(db)

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

    async def _get(self, key: ContentKey, model: type[ModelT]) -> ModelT | None:
        block = await self.blocks.get(key)
        if block is None:
            return None
        try:
            return model.model_validate(block.data)
        except ValidationError as exc:
            logger.error("Content block %s is invalid (%s): %s", key, type(exc).__name__, exc)
            return None
