import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import MessengerException
from src.core.texts import START_TEXT
from src.providers.messenger_provider import MessengerProvider
from src.providers.storage_provider import StorageProvider
from src.repositories.file_repository import FileRepository
from src.services.content_service import ContentService
from src.services.file_service import FileService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WelcomeMessage:
    text: str
    photo_token: str | None


class WelcomeService:
    def __init__(self, db: AsyncSession, messenger: MessengerProvider, storage: StorageProvider):
        self.db = db
        self.messenger = messenger
        self.storage = storage
        self.content = ContentService(db)
        self.files = FileRepository(db)
        self.file_service = FileService(db, storage)

    async def get_message(self) -> WelcomeMessage:
        content = await self.content.get_welcome()
        if content is None:
            return WelcomeMessage(text=START_TEXT, photo_token=None)
        photo_token = await self._photo_token(content.file_id)
        return WelcomeMessage(text=content.text, photo_token=photo_token)

    async def _photo_token(self, file_id: int | None) -> str | None:
        if file_id is None:
            return None

        file = await self.files.get_by_id(file_id)
        if file is None:
            logger.error("Welcome photo file %s not found", file_id)
            return None

        try:
            return await self.file_service.get_max_token(file, self.messenger)
        except (OSError, MessengerException) as exc:
            logger.warning("Welcome photo unavailable: %s", type(exc).__name__)
            return None
