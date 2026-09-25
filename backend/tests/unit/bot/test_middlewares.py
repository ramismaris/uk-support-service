from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from maxapi.types import BotStarted, MessageCallback, MessageCreated, MessageRemoved

from src.bot.middlewares import UserSyncMiddleware


def _make_sender(
    user_id: int = 42,
    first_name: str = "Иван",
    last_name: str | None = "Петров",
    username: str | None = "ivan",
) -> MagicMock:
    sender = MagicMock()
    sender.user_id = user_id
    sender.first_name = first_name
    sender.last_name = last_name
    sender.username = username
    return sender


def _message_created(sender: MagicMock | None) -> MagicMock:
    event = MagicMock(spec=MessageCreated)
    message = MagicMock()
    message.sender = sender
    event.message = message
    return event


def _bot_started(user: MagicMock) -> MagicMock:
    event = MagicMock(spec=BotStarted)
    event.user = user
    return event


def _message_callback(user: MagicMock) -> MagicMock:
    event = MagicMock(spec=MessageCallback)
    callback = MagicMock()
    callback.user = user
    event.callback = callback
    return event


@pytest.fixture
def session_local() -> tuple[MagicMock, MagicMock]:
    session = MagicMock()
    context_manager = MagicMock()
    context_manager.__aenter__ = AsyncMock(return_value=session)
    context_manager.__aexit__ = AsyncMock(return_value=False)
    local = MagicMock(return_value=context_manager)
    with patch("src.bot.middlewares.AsyncSessionLocal", local):
        yield local, session


@pytest.fixture
def user_service() -> MagicMock:
    service = MagicMock()
    service.sync_from_max = AsyncMock()
    with patch("src.bot.middlewares.UserService", return_value=service):
        yield service


def _make_db_user(is_blocked: bool = False) -> MagicMock:
    user = MagicMock()
    user.is_blocked = is_blocked
    return user


async def test_message_created_syncs_user(
    session_local: tuple[MagicMock, MagicMock], user_service: MagicMock
):
    local, session = session_local
    sender = _make_sender()
    db_user = _make_db_user()
    user_service.sync_from_max.return_value = db_user
    event = _message_created(sender)
    data: dict = {}
    handler = AsyncMock()

    await UserSyncMiddleware()(handler, event, data)

    local.assert_called_once()
    user_service.sync_from_max.assert_awaited_once_with(
        max_user_id=42,
        first_name="Иван",
        last_name="Петров",
        username="ivan",
    )
    assert data["db"] is session
    assert data["user"] is db_user
    handler.assert_awaited_once_with(event, data)


async def test_bot_started_syncs_user(
    session_local: tuple[MagicMock, MagicMock], user_service: MagicMock
):
    _, session = session_local
    user = _make_sender()
    db_user = _make_db_user()
    user_service.sync_from_max.return_value = db_user
    event = _bot_started(user)
    data: dict = {}
    handler = AsyncMock()

    await UserSyncMiddleware()(handler, event, data)

    user_service.sync_from_max.assert_awaited_once_with(
        max_user_id=42,
        first_name="Иван",
        last_name="Петров",
        username="ivan",
    )
    assert data["db"] is session
    assert data["user"] is db_user
    handler.assert_awaited_once_with(event, data)


async def test_message_callback_syncs_user(
    session_local: tuple[MagicMock, MagicMock], user_service: MagicMock
):
    _, session = session_local
    user = _make_sender()
    db_user = _make_db_user()
    user_service.sync_from_max.return_value = db_user
    event = _message_callback(user)
    data: dict = {}
    handler = AsyncMock()

    await UserSyncMiddleware()(handler, event, data)

    user_service.sync_from_max.assert_awaited_once_with(
        max_user_id=42,
        first_name="Иван",
        last_name="Петров",
        username="ivan",
    )
    assert data["db"] is session
    assert data["user"] is db_user
    handler.assert_awaited_once_with(event, data)


async def test_blocked_user_skips_handler(
    session_local: tuple[MagicMock, MagicMock], user_service: MagicMock
):
    user_service.sync_from_max.return_value = _make_db_user(is_blocked=True)
    event = _message_created(_make_sender())
    data: dict = {}
    handler = AsyncMock()

    await UserSyncMiddleware()(handler, event, data)

    handler.assert_not_awaited()
    assert "db" not in data
    assert "user" not in data


async def test_update_without_person_is_passed_through(
    session_local: tuple[MagicMock, MagicMock], user_service: MagicMock
):
    local, _ = session_local
    event = MagicMock(spec=MessageRemoved)
    data: dict = {}
    handler = AsyncMock()

    await UserSyncMiddleware()(handler, event, data)

    user_service.sync_from_max.assert_not_awaited()
    local.assert_not_called()
    handler.assert_awaited_once_with(event, data)


async def test_message_without_sender_is_passed_through(
    session_local: tuple[MagicMock, MagicMock], user_service: MagicMock
):
    local, _ = session_local
    event = _message_created(None)
    data: dict = {}
    handler = AsyncMock()

    await UserSyncMiddleware()(handler, event, data)

    user_service.sync_from_max.assert_not_awaited()
    local.assert_not_called()
    handler.assert_awaited_once_with(event, data)
