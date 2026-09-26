from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.config import settings
from src.core.constants import BIGINT_MAX, UserRole
from src.core.exceptions import AppException, NotFoundException
from src.core.texts import USER_CANNOT_CHANGE_SELF, USER_CONFIG_ADMIN, USER_NOT_FOUND
from src.core.ws_manager import WS_FORBIDDEN
from src.services.user_service import UserService


def _make_user(
    role: UserRole = UserRole.CLIENT,
    *,
    id: int = 1,
    max_user_id: int = 42,
    is_blocked: bool = False,
) -> MagicMock:
    user = MagicMock()
    user.id = id
    user.max_user_id = max_user_id
    user.role = role
    user.is_blocked = is_blocked
    user.last_seen_at = None
    return user


@pytest.fixture
def users_repo() -> MagicMock:
    repo = MagicMock()
    repo.get_by_max_user_id = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.create = AsyncMock()
    repo.list = AsyncMock()
    repo.count = AsyncMock()
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


async def _list_for_admin(
    users_repo: MagicMock,
    db: AsyncMock,
    *,
    roles=None,
    is_blocked=None,
    q=None,
    skip=0,
    limit=50,
):
    with patch("src.services.user_service.UserRepository", return_value=users_repo):
        return await UserService(db).list_for_admin(
            roles=roles, is_blocked=is_blocked, q=q, skip=skip, limit=limit
        )


async def test_list_for_admin_passes_filters_through(users_repo: MagicMock):
    users_repo.list.return_value = ["user"]
    users_repo.count.return_value = 7
    db = AsyncMock()

    users, total = await _list_for_admin(
        users_repo,
        db,
        roles=[UserRole.MANAGER, UserRole.ADMIN],
        is_blocked=False,
        q="иван",
        skip=10,
        limit=20,
    )

    users_repo.list.assert_awaited_once_with(
        roles=[UserRole.MANAGER, UserRole.ADMIN],
        is_blocked=False,
        search="иван",
        max_user_id=None,
        skip=10,
        limit=20,
    )
    users_repo.count.assert_awaited_once_with(
        roles=[UserRole.MANAGER, UserRole.ADMIN],
        is_blocked=False,
        search="иван",
        max_user_id=None,
    )
    assert users == ["user"]
    assert total == 7


async def test_list_for_admin_strips_q_and_blank_q_means_no_search(users_repo: MagicMock):
    users_repo.list.return_value = []
    users_repo.count.return_value = 0
    db = AsyncMock()

    await _list_for_admin(users_repo, db, q="  иван  ")
    assert users_repo.list.await_args.kwargs["search"] == "иван"

    await _list_for_admin(users_repo, db, q="   ")
    assert users_repo.list.await_args.kwargs["search"] is None
    assert users_repo.list.await_args.kwargs["max_user_id"] is None

    await _list_for_admin(users_repo, db, q=None)
    assert users_repo.list.await_args.kwargs["search"] is None


async def test_list_for_admin_digits_add_max_user_id(users_repo: MagicMock):
    users_repo.list.return_value = []
    users_repo.count.return_value = 0
    db = AsyncMock()

    await _list_for_admin(users_repo, db, q="1000003")

    assert users_repo.list.await_args.kwargs["search"] == "1000003"
    assert users_repo.list.await_args.kwargs["max_user_id"] == 1000003


@pytest.mark.parametrize("q", ["²", "12a", "1" * 20, str(BIGINT_MAX + 1)])
async def test_list_for_admin_non_numeric_or_too_large_digits_skip_max_user_id(
    users_repo: MagicMock, q: str
):
    users_repo.list.return_value = []
    users_repo.count.return_value = 0
    db = AsyncMock()

    await _list_for_admin(users_repo, db, q=q)

    assert users_repo.list.await_args.kwargs["search"] == q
    assert users_repo.list.await_args.kwargs["max_user_id"] is None


async def _update_by_admin(
    users_repo: MagicMock,
    db: AsyncMock,
    *,
    admin: MagicMock,
    user_id: int,
    role=None,
    is_blocked=None,
    admin_max_user_ids=None,
    ws_manager=None,
):
    with (
        patch("src.services.user_service.UserRepository", return_value=users_repo),
        patch.object(settings, "admin_max_user_ids", admin_max_user_ids or []),
        patch("src.services.user_service.ws_manager", ws_manager),
    ):
        return await UserService(db).update_by_admin(
            user_id, admin, role=role, is_blocked=is_blocked
        )


async def test_update_by_admin_unknown_user_returns_404(users_repo: MagicMock):
    users_repo.get_by_id.return_value = None
    admin = _make_user(UserRole.ADMIN, id=10)
    db = AsyncMock()

    with pytest.raises(NotFoundException) as exc:
        await _update_by_admin(users_repo, db, admin=admin, user_id=999)

    assert exc.value.message == USER_NOT_FOUND
    db.commit.assert_not_awaited()


async def test_update_by_admin_self_demotion_and_block_are_conflicts(users_repo: MagicMock):
    admin = _make_user(UserRole.ADMIN, id=10)
    users_repo.get_by_id.return_value = admin
    db = AsyncMock()

    with pytest.raises(AppException) as exc:
        await _update_by_admin(users_repo, db, admin=admin, user_id=10, role=UserRole.MANAGER)
    assert exc.value.status_code == 409
    assert exc.value.message == USER_CANNOT_CHANGE_SELF

    with pytest.raises(AppException) as exc:
        await _update_by_admin(users_repo, db, admin=admin, user_id=10, role=UserRole.CLIENT)
    assert exc.value.status_code == 409

    with pytest.raises(AppException) as exc:
        await _update_by_admin(users_repo, db, admin=admin, user_id=10, is_blocked=True)
    assert exc.value.status_code == 409

    db.commit.assert_not_awaited()


async def test_update_by_admin_self_noop_is_allowed(users_repo: MagicMock):
    admin = _make_user(UserRole.ADMIN, id=10)
    users_repo.get_by_id.return_value = admin
    db = AsyncMock()

    result = await _update_by_admin(
        users_repo, db, admin=admin, user_id=10, role=UserRole.ADMIN, is_blocked=False
    )

    assert result is admin
    db.commit.assert_awaited_once()


async def test_update_by_admin_config_admin_cannot_lose_rights(users_repo: MagicMock):
    admin = _make_user(UserRole.ADMIN, id=10, max_user_id=999)
    target = _make_user(UserRole.ADMIN, id=20, max_user_id=123)
    users_repo.get_by_id.return_value = target
    db = AsyncMock()

    with pytest.raises(AppException) as exc:
        await _update_by_admin(
            users_repo,
            db,
            admin=admin,
            user_id=20,
            role=UserRole.MANAGER,
            admin_max_user_ids=[123],
        )
    assert exc.value.status_code == 409
    assert exc.value.message == USER_CONFIG_ADMIN

    with pytest.raises(AppException):
        await _update_by_admin(
            users_repo,
            db,
            admin=admin,
            user_id=20,
            is_blocked=True,
            admin_max_user_ids=[123],
        )

    db.commit.assert_not_awaited()


async def test_update_by_admin_config_admin_unblocking_is_allowed(users_repo: MagicMock):
    admin = _make_user(UserRole.ADMIN, id=10)
    target = _make_user(UserRole.ADMIN, id=20, max_user_id=123, is_blocked=True)
    users_repo.get_by_id.return_value = target
    db = AsyncMock()

    result = await _update_by_admin(
        users_repo,
        db,
        admin=admin,
        user_id=20,
        is_blocked=False,
        admin_max_user_ids=[123],
    )

    assert result is target
    assert target.is_blocked is False
    db.commit.assert_awaited_once()


async def test_update_by_admin_applies_and_commits(users_repo: MagicMock):
    admin = _make_user(UserRole.ADMIN, id=10)
    target = _make_user(UserRole.MANAGER, id=20)
    users_repo.get_by_id.return_value = target
    db = AsyncMock()
    ws_manager = MagicMock()
    ws_manager.close_user = AsyncMock()

    result = await _update_by_admin(
        users_repo,
        db,
        admin=admin,
        user_id=20,
        role=UserRole.MANAGER,
        is_blocked=True,
        ws_manager=ws_manager,
    )

    assert result is target
    assert target.role == UserRole.MANAGER
    assert target.is_blocked is True
    db.commit.assert_awaited_once()


async def test_update_by_admin_closes_socket_when_blocked(users_repo: MagicMock):
    admin = _make_user(UserRole.ADMIN, id=10)
    target = _make_user(UserRole.MANAGER, id=20)
    users_repo.get_by_id.return_value = target
    db = AsyncMock()
    ws_manager = MagicMock()
    ws_manager.close_user = AsyncMock()

    await _update_by_admin(
        users_repo, db, admin=admin, user_id=20, is_blocked=True, ws_manager=ws_manager
    )

    ws_manager.close_user.assert_awaited_once_with(target.id, WS_FORBIDDEN)


async def test_update_by_admin_closes_socket_when_demoted_to_client(users_repo: MagicMock):
    admin = _make_user(UserRole.ADMIN, id=10)
    target = _make_user(UserRole.MANAGER, id=20)
    users_repo.get_by_id.return_value = target
    db = AsyncMock()
    ws_manager = MagicMock()
    ws_manager.close_user = AsyncMock()

    await _update_by_admin(
        users_repo, db, admin=admin, user_id=20, role=UserRole.CLIENT, ws_manager=ws_manager
    )

    ws_manager.close_user.assert_awaited_once_with(target.id, WS_FORBIDDEN)


async def test_update_by_admin_keeps_socket_for_manager_or_admin(users_repo: MagicMock):
    admin = _make_user(UserRole.ADMIN, id=10)
    db = AsyncMock()
    ws_manager = MagicMock()
    ws_manager.close_user = AsyncMock()

    target = _make_user(UserRole.CLIENT, id=20)
    users_repo.get_by_id.return_value = target
    await _update_by_admin(
        users_repo, db, admin=admin, user_id=20, role=UserRole.MANAGER, ws_manager=ws_manager
    )
    ws_manager.close_user.assert_not_awaited()

    ws_manager.close_user.reset_mock()
    target = _make_user(UserRole.MANAGER, id=21, is_blocked=True)
    users_repo.get_by_id.return_value = target
    await _update_by_admin(
        users_repo, db, admin=admin, user_id=21, is_blocked=False, ws_manager=ws_manager
    )
    ws_manager.close_user.assert_not_awaited()


async def test_update_by_admin_does_not_close_socket_on_error(users_repo: MagicMock):
    admin = _make_user(UserRole.ADMIN, id=10)
    users_repo.get_by_id.return_value = admin
    db = AsyncMock()
    ws_manager = MagicMock()
    ws_manager.close_user = AsyncMock()

    with pytest.raises(AppException):
        await _update_by_admin(
            users_repo, db, admin=admin, user_id=10, is_blocked=True, ws_manager=ws_manager
        )

    ws_manager.close_user.assert_not_awaited()
    db.commit.assert_not_awaited()
