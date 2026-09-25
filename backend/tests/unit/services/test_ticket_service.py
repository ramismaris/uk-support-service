from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.constants import TicketStatus
from src.core.exceptions import NotFoundException
from src.services import ticket_rules
from src.services.ticket_service import TicketService


@pytest.fixture
def tickets_repo() -> MagicMock:
    repo = MagicMock()
    repo.list = AsyncMock(return_value=[])
    repo.count = AsyncMock(return_value=0)
    repo.get_by_id = AsyncMock()
    return repo


@pytest.fixture
def files_repo() -> MagicMock:
    repo = MagicMock()
    repo.list_by_ticket = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def changes_repo() -> MagicMock:
    repo = MagicMock()
    repo.list_by_ticket = AsyncMock(return_value=[])
    return repo


def _service(
    db: MagicMock,
    tickets_repo: MagicMock,
    files_repo: MagicMock,
    changes_repo: MagicMock,
) -> TicketService:
    with (
        patch("src.services.ticket_service.TicketRepository", return_value=tickets_repo),
        patch("src.services.ticket_service.FileRepository", return_value=files_repo),
        patch(
            "src.services.ticket_service.StatusChangeRepository",
            return_value=changes_repo,
        ),
    ):
        return TicketService(db)


def _staff(user_id: int = 42) -> MagicMock:
    staff = MagicMock()
    staff.id = user_id
    return staff


async def test_list_for_staff_uses_open_statuses_by_default(
    tickets_repo: MagicMock, files_repo: MagicMock, changes_repo: MagicMock
) -> None:
    service = _service(AsyncMock(), tickets_repo, files_repo, changes_repo)
    tickets_repo.count.return_value = 3

    items, total = await service.list_for_staff(
        _staff(),
        status=None,
        building_id=None,
        category_id=None,
        mine=False,
        skip=0,
        limit=50,
    )

    assert items == []
    assert total == 3
    tickets_repo.list.assert_awaited_once_with(
        statuses=ticket_rules.OPEN_STATUSES,
        building_id=None,
        category_id=None,
        assignee_id=None,
        skip=0,
        limit=50,
    )
    tickets_repo.count.assert_awaited_once_with(
        statuses=ticket_rules.OPEN_STATUSES,
        building_id=None,
        category_id=None,
        assignee_id=None,
    )


async def test_list_for_staff_uses_given_status_and_filters(
    tickets_repo: MagicMock, files_repo: MagicMock, changes_repo: MagicMock
) -> None:
    service = _service(AsyncMock(), tickets_repo, files_repo, changes_repo)

    await service.list_for_staff(
        _staff(),
        status=TicketStatus.IN_PROGRESS,
        building_id=7,
        category_id=8,
        mine=False,
        skip=5,
        limit=10,
    )

    tickets_repo.list.assert_awaited_once_with(
        statuses=[TicketStatus.IN_PROGRESS],
        building_id=7,
        category_id=8,
        assignee_id=None,
        skip=5,
        limit=10,
    )


async def test_list_for_staff_mine_sets_assignee(
    tickets_repo: MagicMock, files_repo: MagicMock, changes_repo: MagicMock
) -> None:
    service = _service(AsyncMock(), tickets_repo, files_repo, changes_repo)

    await service.list_for_staff(
        _staff(user_id=42),
        status=None,
        building_id=None,
        category_id=None,
        mine=True,
        skip=0,
        limit=50,
    )

    assert tickets_repo.list.await_args.kwargs["assignee_id"] == 42
    assert tickets_repo.count.await_args.kwargs["assignee_id"] == 42


async def test_get_for_staff_returns_ticket_files_and_history(
    tickets_repo: MagicMock, files_repo: MagicMock, changes_repo: MagicMock
) -> None:
    service = _service(AsyncMock(), tickets_repo, files_repo, changes_repo)
    ticket = MagicMock()
    file = MagicMock()
    change = MagicMock()
    tickets_repo.get_by_id.return_value = ticket
    files_repo.list_by_ticket.return_value = [file]
    changes_repo.list_by_ticket.return_value = [change]

    result = await service.get_for_staff(5)

    assert result == (ticket, [file], [change])
    files_repo.list_by_ticket.assert_awaited_once_with(5)
    changes_repo.list_by_ticket.assert_awaited_once_with(5)


async def test_get_for_staff_missing_ticket_raises_not_found(
    tickets_repo: MagicMock, files_repo: MagicMock, changes_repo: MagicMock
) -> None:
    service = _service(AsyncMock(), tickets_repo, files_repo, changes_repo)
    tickets_repo.get_by_id.return_value = None

    with pytest.raises(NotFoundException):
        await service.get_for_staff(999)
