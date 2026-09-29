from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from src.core.constants import DIRECTORY_ACTIVE_LIMIT
from src.core.exceptions import ConflictException, NotFoundException
from src.core.texts import (
    BUILDING_EXISTS,
    BUILDING_LAST_ACTIVE,
    BUILDING_NOT_FOUND,
    BUILDINGS_LIMIT,
)
from src.services.building_service import BuildingService

DUPLICATE = IntegrityError("INSERT", {}, Exception("duplicate key"))


def _make_building(
    *,
    id: int = 1,
    address: str = "ул. Мира, 1",
    is_active: bool = True,
) -> MagicMock:
    building = MagicMock()
    building.id = id
    building.address = address
    building.is_active = is_active
    return building


@pytest.fixture
def buildings_repo() -> MagicMock:
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    repo.list_active = AsyncMock()
    repo.list_all = AsyncMock()
    repo.count_active = AsyncMock()
    repo.create = AsyncMock()
    return repo


def _service(buildings_repo: MagicMock, db: MagicMock) -> BuildingService:
    with patch("src.services.building_service.BuildingRepository", return_value=buildings_repo):
        return BuildingService(db)


# --- create ---


async def test_create_at_limit_is_conflict_and_creates_nothing(buildings_repo: MagicMock):
    buildings_repo.count_active.return_value = DIRECTORY_ACTIVE_LIMIT
    db = AsyncMock()

    with pytest.raises(ConflictException) as exc:
        await _service(buildings_repo, db).create("ул. Мира, 1")

    assert exc.value.message == BUILDINGS_LIMIT
    buildings_repo.create.assert_not_awaited()
    db.commit.assert_not_awaited()


async def test_create_below_limit_creates_and_commits(buildings_repo: MagicMock):
    building = _make_building()
    buildings_repo.count_active.return_value = DIRECTORY_ACTIVE_LIMIT - 1
    buildings_repo.create.return_value = building
    db = AsyncMock()

    result = await _service(buildings_repo, db).create("ул. Мира, 1")

    assert result is building
    buildings_repo.create.assert_awaited_once_with("ул. Мира, 1")
    db.commit.assert_awaited_once()


async def test_create_duplicate_rolls_back_and_is_conflict(buildings_repo: MagicMock):
    buildings_repo.count_active.return_value = 0
    buildings_repo.create.side_effect = DUPLICATE
    db = AsyncMock()

    with pytest.raises(ConflictException) as exc:
        await _service(buildings_repo, db).create("ул. Мира, 1")

    assert exc.value.message == BUILDING_EXISTS
    db.rollback.assert_awaited_once()
    db.commit.assert_not_awaited()


# --- update ---


async def test_update_unknown_is_not_found(buildings_repo: MagicMock):
    buildings_repo.get_by_id.return_value = None
    db = AsyncMock()

    with pytest.raises(NotFoundException) as exc:
        await _service(buildings_repo, db).update(999, address="ул. Мира, 1", is_active=None)

    assert exc.value.message == BUILDING_NOT_FOUND
    db.commit.assert_not_awaited()


async def test_update_enables_disabled_at_limit_is_conflict_and_unchanged(
    buildings_repo: MagicMock,
):
    building = _make_building(is_active=False)
    buildings_repo.get_by_id.return_value = building
    buildings_repo.count_active.return_value = DIRECTORY_ACTIVE_LIMIT
    db = AsyncMock()

    with pytest.raises(ConflictException) as exc:
        await _service(buildings_repo, db).update(1, address=None, is_active=True)

    assert exc.value.message == BUILDINGS_LIMIT
    assert building.is_active is False
    db.flush.assert_not_awaited()
    db.commit.assert_not_awaited()


async def test_update_enabling_already_enabled_at_limit_is_allowed(buildings_repo: MagicMock):
    building = _make_building(is_active=True)
    buildings_repo.get_by_id.return_value = building
    buildings_repo.count_active.return_value = DIRECTORY_ACTIVE_LIMIT
    db = AsyncMock()

    result = await _service(buildings_repo, db).update(1, address=None, is_active=True)

    assert result is building
    assert building.is_active is True
    db.commit.assert_awaited_once()


async def test_update_disabling_last_active_is_conflict_and_unchanged(buildings_repo: MagicMock):
    building = _make_building(is_active=True)
    buildings_repo.get_by_id.return_value = building
    buildings_repo.count_active.return_value = 1
    db = AsyncMock()

    with pytest.raises(ConflictException) as exc:
        await _service(buildings_repo, db).update(1, address=None, is_active=False)

    assert exc.value.message == BUILDING_LAST_ACTIVE
    assert building.is_active is True
    db.flush.assert_not_awaited()
    db.commit.assert_not_awaited()


async def test_update_disabling_when_two_enabled_is_allowed(buildings_repo: MagicMock):
    building = _make_building(is_active=True)
    buildings_repo.get_by_id.return_value = building
    buildings_repo.count_active.return_value = 2
    db = AsyncMock()

    await _service(buildings_repo, db).update(1, address=None, is_active=False)

    assert building.is_active is False
    db.commit.assert_awaited_once()


async def test_update_rename_flush_integrity_rolls_back_and_is_conflict(
    buildings_repo: MagicMock,
):
    building = _make_building(address="ул. Мира, 1")
    buildings_repo.get_by_id.return_value = building
    db = AsyncMock()
    db.flush.side_effect = DUPLICATE

    with pytest.raises(ConflictException) as exc:
        await _service(buildings_repo, db).update(1, address="ул. Ленина, 2", is_active=None)

    assert exc.value.message == BUILDING_EXISTS
    db.rollback.assert_awaited_once()
    db.commit.assert_not_awaited()


async def test_update_none_fields_stay_untouched(buildings_repo: MagicMock):
    building = _make_building(address="ул. Мира, 1", is_active=True)
    buildings_repo.get_by_id.return_value = building
    db = AsyncMock()

    result = await _service(buildings_repo, db).update(1, address=None, is_active=None)

    assert result is building
    assert building.address == "ул. Мира, 1"
    assert building.is_active is True
    buildings_repo.count_active.assert_not_awaited()
    db.commit.assert_awaited_once()
