from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import TicketStatus, TicketType, UserRole
from src.repositories.building_repository import BuildingRepository
from src.repositories.category_repository import CategoryRepository
from src.repositories.status_change_repository import StatusChangeRepository
from src.repositories.ticket_repository import TicketRepository
from src.repositories.user_repository import UserRepository
from src.services.ticket_rules import OPEN_STATUSES

SINCE = datetime(2026, 9, 1, tzinfo=UTC)


async def _make_request(
    db: AsyncSession,
    *,
    client_id: int,
    category_id: int,
    building_id: int,
    status: TicketStatus,
    created_at: datetime,
    closed_at: datetime | None = None,
):
    return await TicketRepository(db).create(
        type=TicketType.REQUEST,
        status=status,
        client_id=client_id,
        description="Течёт кран на кухне",
        category_id=category_id,
        building_id=building_id,
        apartment="45",
        created_at=created_at,
        closed_at=closed_at,
    )


async def test_reacted_at_is_first_change_out_of_new(db: AsyncSession) -> None:
    client = await UserRepository(db).create(max_user_id=1, first_name="Мария")
    building = await BuildingRepository(db).create("ул. Ленина, 12")
    category = await CategoryRepository(db).create("🚰 Сантехника", 1)
    created_new = datetime(2026, 9, 10, 9, 0, tzinfo=UTC)
    created_taken = datetime(2026, 9, 11, 9, 0, tzinfo=UTC)
    taken_at = datetime(2026, 9, 11, 9, 30, tzinfo=UTC)

    still_new = await _make_request(
        db,
        client_id=client.id,
        category_id=category.id,
        building_id=building.id,
        status=TicketStatus.NEW,
        created_at=created_new,
    )
    taken = await _make_request(
        db,
        client_id=client.id,
        category_id=category.id,
        building_id=building.id,
        status=TicketStatus.WAITING_CLIENT,
        created_at=created_taken,
    )
    changes = StatusChangeRepository(db)
    await changes.create(still_new.id, None, TicketStatus.NEW, created_at=created_new)
    await changes.create(taken.id, None, TicketStatus.NEW, created_at=created_taken)
    await changes.create(taken.id, TicketStatus.NEW, TicketStatus.IN_PROGRESS, created_at=taken_at)
    await changes.create(
        taken.id,
        TicketStatus.IN_PROGRESS,
        TicketStatus.WAITING_CLIENT,
        created_at=datetime(2026, 9, 11, 10, 0, tzinfo=UTC),
    )
    await db.commit()

    rows = await TicketRepository(db).list_for_dashboard(since=SINCE, open_statuses=OPEN_STATUSES)

    by_created = {row.created_at: row for row in rows}
    assert by_created[created_taken].reacted_at == taken_at
    assert by_created[created_taken].category_title == "🚰 Сантехника"
    assert by_created[created_taken].category_sort_order == 1
    assert by_created[created_new].reacted_at is None


async def test_filter_includes_created_or_closed_after_since_and_open_tickets(
    db: AsyncSession,
) -> None:
    client = await UserRepository(db).create(max_user_id=1, first_name="Мария")
    building = await BuildingRepository(db).create("ул. Ленина, 12")
    category = await CategoryRepository(db).create("Сантехника", 1)
    created_after = datetime(2026, 9, 5, 9, 0, tzinfo=UTC)
    closed_after = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
    open_old = datetime(2026, 8, 2, 9, 0, tzinfo=UTC)
    closed_old = datetime(2026, 8, 3, 9, 0, tzinfo=UTC)

    await _make_request(
        db,
        client_id=client.id,
        category_id=category.id,
        building_id=building.id,
        status=TicketStatus.NEW,
        created_at=created_after,
    )
    await _make_request(
        db,
        client_id=client.id,
        category_id=category.id,
        building_id=building.id,
        status=TicketStatus.CLOSED,
        created_at=closed_after,
        closed_at=datetime(2026, 9, 3, 9, 0, tzinfo=UTC),
    )
    await _make_request(
        db,
        client_id=client.id,
        category_id=category.id,
        building_id=building.id,
        status=TicketStatus.IN_PROGRESS,
        created_at=open_old,
    )
    await _make_request(
        db,
        client_id=client.id,
        category_id=category.id,
        building_id=building.id,
        status=TicketStatus.CLOSED,
        created_at=closed_old,
        closed_at=datetime(2026, 8, 5, 9, 0, tzinfo=UTC),
    )
    await db.commit()

    rows = await TicketRepository(db).list_for_dashboard(since=SINCE, open_statuses=OPEN_STATUSES)

    assert {row.created_at for row in rows} == {created_after, closed_after, open_old}


async def test_dashboard_row_includes_building_and_assignee(db: AsyncSession) -> None:
    client = await UserRepository(db).create(max_user_id=1, first_name="Мария")
    manager = await UserRepository(db).create(
        max_user_id=2, first_name="Пётр", role=UserRole.MANAGER
    )
    building = await BuildingRepository(db).create("ул. Ленина, 12")
    category = await CategoryRepository(db).create("🚰 Сантехника", 1)
    created_at = datetime(2026, 9, 10, 9, 0, tzinfo=UTC)

    await TicketRepository(db).create(
        type=TicketType.REQUEST,
        status=TicketStatus.NEW,
        client_id=client.id,
        description="Течёт кран на кухне",
        category_id=category.id,
        building_id=building.id,
        apartment="45",
        assignee_id=manager.id,
        created_at=created_at,
    )
    await db.commit()

    rows = await TicketRepository(db).list_for_dashboard(since=SINCE, open_statuses=OPEN_STATUSES)

    row = next(row for row in rows if row.created_at == created_at)
    assert row.building_id == building.id
    assert row.building_address == "ул. Ленина, 12"
    assert row.assignee_id == manager.id


async def test_dashboard_row_without_building_and_assignee_is_none(db: AsyncSession) -> None:
    client = await UserRepository(db).create(max_user_id=1, first_name="Мария")
    created_at = datetime(2026, 9, 10, 9, 0, tzinfo=UTC)

    await TicketRepository(db).create(
        type=TicketType.QUESTION,
        status=TicketStatus.NEW,
        client_id=client.id,
        description="Как передать показания?",
        created_at=created_at,
    )
    await db.commit()

    rows = await TicketRepository(db).list_for_dashboard(since=SINCE, open_statuses=OPEN_STATUSES)

    row = next(row for row in rows if row.created_at == created_at)
    assert row.building_id is None
    assert row.building_address is None
    assert row.assignee_id is None
