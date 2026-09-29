from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from src.core.constants import DIRECTORY_ACTIVE_LIMIT
from src.core.exceptions import ConflictException, NotFoundException
from src.core.texts import (
    CATEGORIES_LIMIT,
    CATEGORY_EXISTS,
    CATEGORY_LAST_ACTIVE,
    CATEGORY_NOT_FOUND,
    CATEGORY_ORDER_STALE,
)
from src.services.category_service import CategoryService

DUPLICATE = IntegrityError("INSERT", {}, Exception("duplicate key"))


def _make_category(
    *,
    id: int = 1,
    title: str = "Сантехника",
    sort_order: int = 1,
    is_active: bool = True,
) -> MagicMock:
    category = MagicMock()
    category.id = id
    category.title = title
    category.sort_order = sort_order
    category.is_active = is_active
    return category


@pytest.fixture
def categories_repo() -> MagicMock:
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    repo.list_active = AsyncMock()
    repo.list_all = AsyncMock()
    repo.count_active = AsyncMock()
    repo.max_sort_order = AsyncMock()
    repo.create = AsyncMock()
    return repo


def _service(categories_repo: MagicMock, db: MagicMock) -> CategoryService:
    with patch("src.services.category_service.CategoryRepository", return_value=categories_repo):
        return CategoryService(db)


# --- create ---


async def test_create_at_limit_is_conflict_and_creates_nothing(categories_repo: MagicMock):
    categories_repo.count_active.return_value = DIRECTORY_ACTIVE_LIMIT
    db = AsyncMock()

    with pytest.raises(ConflictException) as exc:
        await _service(categories_repo, db).create("Сантехника")

    assert exc.value.message == CATEGORIES_LIMIT
    categories_repo.create.assert_not_awaited()
    db.commit.assert_not_awaited()


async def test_create_below_limit_appends_after_max_sort_order(categories_repo: MagicMock):
    category = _make_category(sort_order=4)
    categories_repo.count_active.return_value = 0
    categories_repo.max_sort_order.return_value = 3
    categories_repo.create.return_value = category
    db = AsyncMock()

    result = await _service(categories_repo, db).create("Сантехника")

    assert result is category
    categories_repo.create.assert_awaited_once_with("Сантехника", 4)
    db.commit.assert_awaited_once()


async def test_create_on_empty_table_gets_sort_order_one(categories_repo: MagicMock):
    category = _make_category(sort_order=1)
    categories_repo.count_active.return_value = 0
    categories_repo.max_sort_order.return_value = 0
    categories_repo.create.return_value = category
    db = AsyncMock()

    await _service(categories_repo, db).create("Сантехника")

    categories_repo.create.assert_awaited_once_with("Сантехника", 1)
    db.commit.assert_awaited_once()


async def test_create_duplicate_rolls_back_and_is_conflict(categories_repo: MagicMock):
    categories_repo.count_active.return_value = 0
    categories_repo.max_sort_order.return_value = 0
    categories_repo.create.side_effect = DUPLICATE
    db = AsyncMock()

    with pytest.raises(ConflictException) as exc:
        await _service(categories_repo, db).create("Сантехника")

    assert exc.value.message == CATEGORY_EXISTS
    db.rollback.assert_awaited_once()
    db.commit.assert_not_awaited()


# --- update ---


async def test_update_unknown_is_not_found(categories_repo: MagicMock):
    categories_repo.get_by_id.return_value = None
    db = AsyncMock()

    with pytest.raises(NotFoundException) as exc:
        await _service(categories_repo, db).update(999, title="Сантехника", is_active=None)

    assert exc.value.message == CATEGORY_NOT_FOUND
    db.commit.assert_not_awaited()


async def test_update_enables_disabled_at_limit_is_conflict_and_unchanged(
    categories_repo: MagicMock,
):
    category = _make_category(is_active=False)
    categories_repo.get_by_id.return_value = category
    categories_repo.count_active.return_value = DIRECTORY_ACTIVE_LIMIT
    db = AsyncMock()

    with pytest.raises(ConflictException) as exc:
        await _service(categories_repo, db).update(1, title=None, is_active=True)

    assert exc.value.message == CATEGORIES_LIMIT
    assert category.is_active is False
    db.flush.assert_not_awaited()
    db.commit.assert_not_awaited()


async def test_update_enabling_already_enabled_at_limit_is_allowed(categories_repo: MagicMock):
    category = _make_category(is_active=True)
    categories_repo.get_by_id.return_value = category
    categories_repo.count_active.return_value = DIRECTORY_ACTIVE_LIMIT
    db = AsyncMock()

    result = await _service(categories_repo, db).update(1, title=None, is_active=True)

    assert result is category
    assert category.is_active is True
    db.commit.assert_awaited_once()


async def test_update_disabling_last_active_is_conflict_and_unchanged(categories_repo: MagicMock):
    category = _make_category(is_active=True)
    categories_repo.get_by_id.return_value = category
    categories_repo.count_active.return_value = 1
    db = AsyncMock()

    with pytest.raises(ConflictException) as exc:
        await _service(categories_repo, db).update(1, title=None, is_active=False)

    assert exc.value.message == CATEGORY_LAST_ACTIVE
    assert category.is_active is True
    db.commit.assert_not_awaited()


async def test_update_disabling_when_two_enabled_is_allowed(categories_repo: MagicMock):
    category = _make_category(is_active=True)
    categories_repo.get_by_id.return_value = category
    categories_repo.count_active.return_value = 2
    db = AsyncMock()

    await _service(categories_repo, db).update(1, title=None, is_active=False)

    assert category.is_active is False
    db.commit.assert_awaited_once()


async def test_update_rename_flush_integrity_rolls_back_and_is_conflict(
    categories_repo: MagicMock,
):
    category = _make_category(title="Сантехника")
    categories_repo.get_by_id.return_value = category
    db = AsyncMock()
    db.flush.side_effect = DUPLICATE

    with pytest.raises(ConflictException) as exc:
        await _service(categories_repo, db).update(1, title="Электрика", is_active=None)

    assert exc.value.message == CATEGORY_EXISTS
    db.rollback.assert_awaited_once()
    db.commit.assert_not_awaited()


async def test_update_none_fields_stay_untouched(categories_repo: MagicMock):
    category = _make_category(title="Сантехника", is_active=True)
    categories_repo.get_by_id.return_value = category
    db = AsyncMock()

    result = await _service(categories_repo, db).update(1, title=None, is_active=None)

    assert result is category
    assert category.title == "Сантехника"
    assert category.is_active is True
    categories_repo.count_active.assert_not_awaited()
    db.commit.assert_awaited_once()


# --- reorder ---


async def test_reorder_sets_positions_in_the_given_order_and_commits(categories_repo: MagicMock):
    first = _make_category(id=1, sort_order=3)
    second = _make_category(id=2, sort_order=1)
    third = _make_category(id=3, sort_order=2)
    categories_repo.list_all.side_effect = [[first, second, third], [third, second, first]]
    db = AsyncMock()

    result = await _service(categories_repo, db).reorder([3, 2, 1])

    assert first.sort_order == 3
    assert second.sort_order == 2
    assert third.sort_order == 1
    assert result == [third, second, first]
    db.commit.assert_awaited_once()
    assert categories_repo.list_all.await_count == 2


@pytest.mark.parametrize(
    "ids",
    [
        pytest.param([1, 2], id="missing-id"),
        pytest.param([1, 2, 4], id="unknown-id"),
        pytest.param([1, 1, 3], id="duplicate"),
        pytest.param([1, 2, 3, 1], id="full-set-plus-duplicate"),
        pytest.param([1, 2, 3, 4], id="extra-id"),
    ],
)
async def test_reorder_stale_set_is_conflict_and_changes_nothing(
    categories_repo: MagicMock, ids: list[int]
):
    first = _make_category(id=1, sort_order=1)
    second = _make_category(id=2, sort_order=2)
    third = _make_category(id=3, sort_order=3)
    categories_repo.list_all.return_value = [first, second, third]
    db = AsyncMock()

    with pytest.raises(ConflictException) as exc:
        await _service(categories_repo, db).reorder(ids)

    assert exc.value.message == CATEGORY_ORDER_STALE
    assert (first.sort_order, second.sort_order, third.sort_order) == (1, 2, 3)
    db.commit.assert_not_awaited()
    assert categories_repo.list_all.await_count == 1
