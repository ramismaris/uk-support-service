from unittest.mock import AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.constants import ContentKey
from src.providers.local_storage_provider import LocalStorageProvider
from src.repositories.content_block_repository import ContentBlockRepository
from src.repositories.file_repository import FileRepository
from src.services.file_service import FileService
from src.services.welcome_service import WelcomeMessage, WelcomeService


async def _add_welcome_block(db: AsyncSession, text: str, file_id: int) -> None:
    await ContentBlockRepository(db).create(ContentKey.WELCOME, {"text": text, "file_id": file_id})
    await db.commit()


async def test_welcome_uploads_photo_once_and_caches_token(
    db: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path,
) -> None:
    storage = LocalStorageProvider(str(tmp_path))
    photo = await FileService(db, storage).save(b"img", "image/webp", "a.webp")
    await _add_welcome_block(db, "Добро пожаловать", photo.id)

    messenger = AsyncMock()
    messenger.upload_file.return_value = "tok-1"
    service = WelcomeService(db, messenger, storage)

    first = await service.get_message()

    assert first == WelcomeMessage(text="Добро пожаловать", photo_token="tok-1")
    messenger.upload_file.assert_awaited_once_with(b"img", "image/webp", "a.webp")

    async with session_factory() as other:
        stored = await FileRepository(other).get_by_id(photo.id)
        assert stored is not None
        assert stored.max_token == "tok-1"

    second = await service.get_message()

    assert second == WelcomeMessage(text="Добро пожаловать", photo_token="tok-1")
    assert messenger.upload_file.await_count == 1
