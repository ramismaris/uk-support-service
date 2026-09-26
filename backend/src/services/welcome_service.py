import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import MessengerException
from src.core.texts import START_TEXT
from src.providers.messenger_provider import MessengerProvider
from src.providers.storage_provider import StorageProvider
from src.repositories.file_repository import FileRepository
from src.services.content_service import ContentService

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
        if file.max_token:
            return file.max_token

        try:
            data = await self.storage.read(file.storage_key)
            token = await self.messenger.upload_file(data, file.mime, file.original_name)
        except (OSError, MessengerException) as exc:
            logger.warning("Welcome photo unavailable: %s", type(exc).__name__)
            return None
        if token is None:
            return None

        file.max_token = token
        await self.db.commit()
        return token
