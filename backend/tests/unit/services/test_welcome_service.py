import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exceptions import MessengerException
from src.core.texts import START_TEXT
from src.schemas.content import WelcomeContent
from src.services.welcome_service import WelcomeMessage, WelcomeService


@pytest.fixture
def env() -> SimpleNamespace:
    db = AsyncMock()
    messenger = AsyncMock()
    storage = MagicMock()
    storage.read = AsyncMock()

    content = MagicMock()
    content.get_welcome = AsyncMock(return_value=WelcomeContent(text="Добро пожаловать", file_id=5))

    file = MagicMock()
    file.storage_key = "files/a.webp"
    file.mime = "image/webp"
    file.original_name = "a.webp"
    file.max_token = None

    files = MagicMock()
    files.get_by_id = AsyncMock(return_value=file)

    with (
        patch("src.services.welcome_service.ContentService", return_value=content),
        patch("src.services.welcome_service.FileRepository", return_value=files),
    ):
        service = WelcomeService(db, messenger, storage)

        yield SimpleNamespace(
            db=db,
            messenger=messenger,
            storage=storage,
            content=content,
            file=file,
            files=files,
            service=service,
        )


async def test_message_with_photo_uploads_and_caches_token(env: SimpleNamespace) -> None:
    env.storage.read.return_value = b"img"
    env.messenger.upload_file.return_value = "tok-1"

    message = await env.service.get_message()

    assert message == WelcomeMessage(text="Добро пожаловать", photo_token="tok-1")
    env.files.get_by_id.assert_awaited_once_with(5)
    env.storage.read.assert_awaited_once_with("files/a.webp")
    env.messenger.upload_file.assert_awaited_once_with(b"img", "image/webp", "a.webp")
    assert env.file.max_token == "tok-1"
    env.db.commit.assert_awaited_once()


async def test_message_uses_cached_token(env: SimpleNamespace) -> None:
    env.file.max_token = "cached"

    message = await env.service.get_message()

    assert message == WelcomeMessage(text="Добро пожаловать", photo_token="cached")
    env.storage.read.assert_not_awaited()
    env.messenger.upload_file.assert_not_awaited()
    env.db.commit.assert_not_awaited()


async def test_message_without_content_block_falls_back(env: SimpleNamespace) -> None:
    env.content.get_welcome.return_value = None

    message = await env.service.get_message()

    assert message == WelcomeMessage(text=START_TEXT, photo_token=None)
    env.files.get_by_id.assert_not_awaited()
    env.storage.read.assert_not_awaited()
    env.messenger.upload_file.assert_not_awaited()
    env.db.commit.assert_not_awaited()


async def test_message_without_file_id_has_no_photo(env: SimpleNamespace) -> None:
    env.content.get_welcome.return_value = WelcomeContent(text="Добро пожаловать")

    message = await env.service.get_message()

    assert message == WelcomeMessage(text="Добро пожаловать", photo_token=None)
    env.files.get_by_id.assert_not_awaited()
    env.db.commit.assert_not_awaited()


async def test_missing_file_row_has_no_photo(
    env: SimpleNamespace, caplog: pytest.LogCaptureFixture
) -> None:
    env.files.get_by_id.return_value = None

    with caplog.at_level(logging.ERROR, logger="src.services.welcome_service"):
        message = await env.service.get_message()

    assert message == WelcomeMessage(text="Добро пожаловать", photo_token=None)
    assert "5" in caplog.text
    env.storage.read.assert_not_awaited()
    env.messenger.upload_file.assert_not_awaited()
    env.db.commit.assert_not_awaited()


async def test_storage_error_has_no_photo(
    env: SimpleNamespace, caplog: pytest.LogCaptureFixture
) -> None:
    env.storage.read.side_effect = FileNotFoundError("gone")

    with caplog.at_level(logging.WARNING, logger="src.services.welcome_service"):
        message = await env.service.get_message()

    assert message == WelcomeMessage(text="Добро пожаловать", photo_token=None)
    assert "FileNotFoundError" in caplog.text
    env.messenger.upload_file.assert_not_awaited()
    assert env.file.max_token is None
    env.db.commit.assert_not_awaited()


async def test_upload_error_has_no_photo(
    env: SimpleNamespace, caplog: pytest.LogCaptureFixture
) -> None:
    env.storage.read.return_value = b"img"
    env.messenger.upload_file.side_effect = MessengerException()

    with caplog.at_level(logging.WARNING, logger="src.services.welcome_service"):
        message = await env.service.get_message()

    assert message == WelcomeMessage(text="Добро пожаловать", photo_token=None)
    assert "MessengerException" in caplog.text
    assert env.file.max_token is None
    env.db.commit.assert_not_awaited()


async def test_messenger_off_stores_nothing(env: SimpleNamespace) -> None:
    env.storage.read.return_value = b"img"
    env.messenger.upload_file.return_value = None

    message = await env.service.get_message()

    assert message == WelcomeMessage(text="Добро пожаловать", photo_token=None)
    env.storage.read.assert_awaited_once_with("files/a.webp")
    env.messenger.upload_file.assert_awaited_once_with(b"img", "image/webp", "a.webp")
    assert env.file.max_token is None
    env.db.commit.assert_not_awaited()
