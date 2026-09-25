from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.config import settings
from src.core.constants import UserRole
from src.services.user_service import UserService


def _make_user(role: UserRole = UserRole.CLIENT) -> MagicMock:
    user = MagicMock()
    user.role = role
    user.last_seen_at = None
    return user


@pytest.fixture
def users_repo() -> MagicMock:
    repo = MagicMock()
    repo.get_by_max_user_id = AsyncMock()
    repo.create = AsyncMock()
    return repo


async def test_sync_creates_new_client(users_repo: MagicMock):
    users_repo.get_by_max_user_id.return_value = None
    users_repo.create.return_value = _make_user()
    db = AsyncMock()

    with (
        patch("src.services.user_service.UserRepository", return_value=users_repo),
        patch.object(settings, "admin_max_user_ids", []),
    ):
        user = await UserService(db).sync_from_max(42, "Иван", "Петров", "ivan")

    users_repo.create.assert_awaited_once_with(
        max_user_id=42,
        first_name="Иван",
        last_name="Петров",
        username="ivan",
        role=UserRole.CLIENT,
    )
    assert user.last_seen_at is not None
    assert user.last_seen_at.tzinfo is not None
    db.commit.assert_awaited_once()


async def test_sync_creates_bootstrap_admin(users_repo: MagicMock):
    users_repo.get_by_max_user_id.return_value = None
    users_repo.create.return_value = _make_user(UserRole.ADMIN)
    db = AsyncMock()

    with (
        patch("src.services.user_service.UserRepository", return_value=users_repo),
        patch.object(settings, "admin_max_user_ids", [42]),
    ):
        await UserService(db).sync_from_max(42, "Иван")

    assert users_repo.create.await_args.kwargs["role"] == UserRole.ADMIN


async def test_sync_promotes_existing_user(users_repo: MagicMock):
    existing = _make_user(UserRole.CLIENT)
    users_repo.get_by_max_user_id.return_value = existing
    db = AsyncMock()

    with (
        patch("src.services.user_service.UserRepository", return_value=users_repo),
        patch.object(settings, "admin_max_user_ids", [42]),
    ):
        user = await UserService(db).sync_from_max(42, "Иван")

    assert user.role == UserRole.ADMIN
    users_repo.create.assert_not_awaited()


async def test_sync_updates_names(users_repo: MagicMock):
    existing = _make_user()
    existing.first_name = "Старое"
    existing.last_name = "Старая"
    existing.username = "old"
    users_repo.get_by_max_user_id.return_value = existing
    db = AsyncMock()

    with (
        patch("src.services.user_service.UserRepository", return_value=users_repo),
        patch.object(settings, "admin_max_user_ids", []),
    ):
        user = await UserService(db).sync_from_max(42, "Новое", "Новая", "new")

    assert user.first_name == "Новое"
    assert user.last_name == "Новая"
    assert user.username == "new"
    assert user.last_seen_at is not None


async def test_sync_stores_empty_optional_names_as_none(users_repo: MagicMock):
    users_repo.get_by_max_user_id.return_value = None
    users_repo.create.return_value = _make_user()
    db = AsyncMock()

    with (
        patch("src.services.user_service.UserRepository", return_value=users_repo),
        patch.object(settings, "admin_max_user_ids", []),
    ):
        await UserService(db).sync_from_max(42, "Иван", "", "")

    users_repo.create.assert_awaited_once_with(
        max_user_id=42,
        first_name="Иван",
        last_name=None,
        username=None,
        role=UserRole.CLIENT,
    )


async def test_sync_updates_empty_optional_names_to_none(users_repo: MagicMock):
    existing = _make_user()
    existing.last_name = "Старая"
    existing.username = "old"
    users_repo.get_by_max_user_id.return_value = existing
    db = AsyncMock()

    with (
        patch("src.services.user_service.UserRepository", return_value=users_repo),
        patch.object(settings, "admin_max_user_ids", []),
    ):
        await UserService(db).sync_from_max(42, "Иван", "", "")

    assert existing.last_name is None
    assert existing.username is None


async def test_sync_does_not_demote_admin(users_repo: MagicMock):
    existing = _make_user(UserRole.ADMIN)
    users_repo.get_by_max_user_id.return_value = existing
    db = AsyncMock()

    with (
        patch("src.services.user_service.UserRepository", return_value=users_repo),
        patch.object(settings, "admin_max_user_ids", []),
    ):
        user = await UserService(db).sync_from_max(42, "Иван")

    assert user.role == UserRole.ADMIN
