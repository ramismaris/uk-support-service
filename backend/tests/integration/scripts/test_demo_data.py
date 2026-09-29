from collections import defaultdict
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from scripts.demo_data import (
    DEMO_MAX_USER_ID_BASE,
    DEMO_RANDOM_SEED,
    OPEN_STATUSES,
    delete_demo,
    ensure_demo,
    reset_demo,
)
from src.core.constants import TicketStatus, TicketType, UserRole
from src.models.building import Building
from src.models.category import Category
from src.models.residence import Residence
from src.models.status_change import StatusChange
from src.models.ticket import Ticket
from src.models.user import User
from src.repositories.building_repository import BuildingRepository
from src.repositories.category_repository import CategoryRepository
from src.repositories.message_repository import MessageRepository
from src.repositories.status_change_repository import StatusChangeRepository
from src.repositories.ticket_repository import TicketRepository
from src.repositories.user_repository import UserRepository
from src.services import ticket_rules
from src.services.dashboard_service import DashboardService

TEST_VOLUME = 0.15

# A status change and its SYSTEM/STAFF/CLIENT message are written a second or
# two apart by the services and by the generator, so «the same moment» allows
# a small window.
_MESSAGE_MOMENT = timedelta(seconds=2)


def _messages_at(messages: list, moment: datetime) -> list:
    return [message for message in messages if abs(message.created_at - moment) <= _MESSAGE_MOMENT]


async def _demo_user_ids(db: AsyncSession) -> list[int]:
    return list(await db.scalars(select(User.id).where(User.max_user_id >= DEMO_MAX_USER_ID_BASE)))


async def _demo_tickets(db: AsyncSession) -> list[Ticket]:
    user_ids = await _demo_user_ids(db)
    return list(
        (
            await db.scalars(
                select(Ticket).where(Ticket.client_id.in_(user_ids)).order_by(Ticket.created_at)
            )
        ).all()
    )


async def _first_demo_tickets(db: AsyncSession, limit: int) -> list[tuple]:
    tickets = await _demo_tickets(db)
    return [
        (
            ticket.created_at,
            ticket.description,
            ticket.status,
            ticket.type,
            ticket.category_id,
            ticket.building_id,
            ticket.apartment,
        )
        for ticket in tickets[:limit]
    ]


async def _count(db: AsyncSession, model: type) -> int:
    return await db.scalar(select(func.count()).select_from(model)) or 0


async def test_generation_is_deterministic(db: AsyncSession) -> None:
    now = datetime.now(UTC)

    first = await reset_demo(db, now=now, volume=TEST_VOLUME, rng_seed=DEMO_RANDOM_SEED)
    await db.commit()
    first_tickets = await _first_demo_tickets(db, 5)

    second = await reset_demo(db, now=now, volume=TEST_VOLUME, rng_seed=DEMO_RANDOM_SEED)
    await db.commit()
    second_tickets = await _first_demo_tickets(db, 5)

    assert first == second
    assert first_tickets == second_tickets


async def test_plain_run_does_not_touch_existing_demo_data(db: AsyncSession) -> None:
    now = datetime.now(UTC)

    created = await ensure_demo(db, now=now, volume=TEST_VOLUME)
    await db.commit()
    assert created is not None
    tickets_before = await _count(db, Ticket)
    users_before = await _count(db, User)

    second = await ensure_demo(db, now=now, volume=TEST_VOLUME)
    await db.commit()

    assert second is None
    assert await _count(db, Ticket) == tickets_before
    assert await _count(db, User) == users_before


async def test_reset_replaces_demo_data_with_same_counts(db: AsyncSession) -> None:
    now = datetime.now(UTC)

    first = await reset_demo(db, now=now, volume=TEST_VOLUME)
    await db.commit()
    second = await reset_demo(db, now=now, volume=TEST_VOLUME)
    await db.commit()

    assert first == second


async def test_delete_removes_demo_data_and_is_safe_to_repeat(db: AsyncSession) -> None:
    now = datetime.now(UTC)
    summary = await reset_demo(db, now=now, volume=TEST_VOLUME)
    await db.commit()

    deleted = await delete_demo(db)
    await db.commit()

    assert deleted.tickets == summary.tickets
    assert await _count(db, Ticket) == 6  # only the base seed tickets are left
    assert await _count(db, User) == 3  # only the base seed users are left
    assert not await _demo_tickets(db)

    again = await delete_demo(db)
    await db.commit()
    assert again.tickets == 0
    assert again.users_deleted == 0


async def test_real_data_survives_reset_and_delete(db: AsyncSession) -> None:
    now = datetime.now(UTC)
    users = UserRepository(db)
    buildings = BuildingRepository(db)
    categories = CategoryRepository(db)
    tickets = TicketRepository(db)
    messages = MessageRepository(db)
    changes = StatusChangeRepository(db)

    real_client = await users.create(max_user_id=5_000_001, first_name="Реальный")
    real_manager = await users.create(
        max_user_id=5_000_002, first_name="Реальный", role=UserRole.MANAGER
    )
    building = await buildings.create("ул. Тестовая, 1")
    category = await categories.create("Тестовая категория", 1)
    await db.flush()
    db.add(
        Residence(
            user_id=real_client.id,
            building_id=building.id,
            apartment="1",
            is_primary=True,
        )
    )
    ticket = await tickets.create(
        type=TicketType.REQUEST,
        status=TicketStatus.IN_PROGRESS,
        client_id=real_client.id,
        description="Реальная заявка",
        category_id=category.id,
        building_id=building.id,
        apartment="1",
    )
    await changes.create(ticket.id, None, TicketStatus.NEW, changed_by_id=real_client.id)
    await changes.create(
        ticket.id, TicketStatus.NEW, TicketStatus.IN_PROGRESS, changed_by_id=real_manager.id
    )
    await messages.create(ticket.id, "CLIENT", author_id=real_client.id, text="Реальное сообщение")
    real_client.active_ticket_id = ticket.id
    await db.commit()

    await reset_demo(db, now=now, volume=TEST_VOLUME)
    await db.commit()

    saved = await db.get(Ticket, ticket.id)
    assert saved is not None
    assert saved.description == "Реальная заявка"
    assert len(await messages.list_by_ticket(ticket.id)) == 1
    assert len(await changes.list_by_ticket(ticket.id)) == 2

    await delete_demo(db)
    await db.commit()

    assert await db.get(Ticket, ticket.id) is not None
    assert await db.get(User, real_client.id) is not None
    assert await db.get(User, real_manager.id) is not None
    assert await db.scalar(select(Residence).where(Residence.user_id == real_client.id))
    refreshed_client = await db.get(User, real_client.id)
    assert refreshed_client is not None and refreshed_client.active_ticket_id == ticket.id


async def test_delete_keeps_demo_manager_referenced_by_real_ticket(db: AsyncSession) -> None:
    now = datetime.now(UTC)
    await reset_demo(db, now=now, volume=TEST_VOLUME)
    await db.commit()

    demo_manager = await db.scalar(
        select(User).where(User.max_user_id >= DEMO_MAX_USER_ID_BASE, User.role == UserRole.MANAGER)
    )
    assert demo_manager is not None

    users = UserRepository(db)
    buildings = BuildingRepository(db)
    categories = CategoryRepository(db)
    real_client = await users.create(max_user_id=5_000_003, first_name="Реальный")
    building = await buildings.create("ул. Тестовая, 2")
    category = await categories.get_by_title("🚰 Сантехника")
    assert category is not None
    await db.flush()
    real_ticket = await TicketRepository(db).create(
        type=TicketType.REQUEST,
        status=TicketStatus.IN_PROGRESS,
        client_id=real_client.id,
        description="Заявка реального жильца",
        category_id=category.id,
        building_id=building.id,
        apartment="7",
        assignee_id=demo_manager.id,
    )
    await db.commit()

    summary = await delete_demo(db)
    await db.commit()

    kept = await db.get(User, demo_manager.id)
    assert kept is not None
    assert summary.users_kept
    assert await db.get(Ticket, real_ticket.id) is not None


async def test_generated_history_is_consistent(db: AsyncSession) -> None:
    now = datetime.now(UTC)
    await reset_demo(db, now=now, volume=TEST_VOLUME)
    await db.commit()

    tickets = await _demo_tickets(db)
    assert tickets
    messages = MessageRepository(db)
    changes = StatusChangeRepository(db)

    for ticket in tickets:
        assert ticket.created_at <= now
        assert ticket.client is not None
        assert ticket.client.max_user_id >= DEMO_MAX_USER_ID_BASE

        if ticket.type == TicketType.REQUEST:
            assert ticket.category_id is not None
            assert ticket.building_id is not None
            assert ticket.apartment is not None
        else:
            assert ticket.category_id is None
            assert ticket.building_id is None
            assert ticket.apartment is None

        history = await changes.list_by_ticket(ticket.id)
        assert history[0].from_status is None
        assert history[0].to_status == TicketStatus.NEW
        assert history[0].changed_by_id == ticket.client_id
        assert history[0].created_at == ticket.created_at
        assert history[-1].to_status == ticket.status
        for index, change in enumerate(history):
            assert change.created_at <= now
            if index == 0:
                continue
            assert history[index - 1].to_status == change.from_status
            assert change.created_at > history[index - 1].created_at
            if change.to_status == TicketStatus.REJECTED:
                assert change.comment
            if (
                change.from_status == TicketStatus.CLOSED
                and change.to_status == TicketStatus.IN_PROGRESS
            ):
                assert change.changed_by_id == ticket.client_id
                closed_at = history[index - 1].created_at
                assert change.created_at - closed_at <= timedelta(days=7)

        closing_changes = [
            change
            for change in history
            if change.to_status in (TicketStatus.CLOSED, TicketStatus.REJECTED)
        ]
        if ticket.status in (TicketStatus.CLOSED, TicketStatus.REJECTED):
            assert ticket.closed_at == closing_changes[-1].created_at
            assert ticket.closed_at <= now
        else:
            assert ticket.closed_at is None

        if ticket.status == TicketStatus.CLOSED:
            assert ticket.rating is None or 1 <= ticket.rating <= 5
        else:
            assert ticket.rating is None

        chat = await messages.list_by_ticket(ticket.id)
        assert 1 <= len(chat) <= 6
        for index, message in enumerate(chat):
            assert message.created_at <= now
            assert message.created_at >= ticket.created_at
            if index:
                assert message.created_at > chat[index - 1].created_at

        # The status history must be written the way the real services write it.
        for change in history[1:]:
            nearby = _messages_at(chat, change.created_at)
            if (
                change.from_status == TicketStatus.NEW
                and change.to_status == TicketStatus.IN_PROGRESS
                and ticket.status in OPEN_STATUSES
            ):
                # message_service moves NEW to IN_PROGRESS on the first staff
                # reply: changed_by_id is None and a STAFF message lands at the
                # same moment. A closed ticket may instead be taken into work by
                # change_by_staff (changed_by_id = manager + SYSTEM message).
                assert change.changed_by_id is None
                assert any(message.sender_type == "STAFF" for message in nearby)
            if (
                change.to_status
                in (TicketStatus.WAITING_CLIENT, TicketStatus.CLOSED, TicketStatus.REJECTED)
                and change.changed_by_id is not None
            ):
                # status_service.change_by_staff writes the SYSTEM message via
                # notification_service.send_status_message.
                assert any(message.sender_type == "SYSTEM" for message in nearby)
            if (
                change.from_status == TicketStatus.WAITING_CLIENT
                and change.to_status == TicketStatus.IN_PROGRESS
            ):
                # message_service's client message path.
                assert change.changed_by_id is None
                assert any(message.sender_type == "CLIENT" for message in nearby)

        client_messages = [message for message in chat if message.sender_type == "CLIENT"]
        if client_messages:
            assert ticket.last_client_message_at == client_messages[-1].created_at
        else:
            assert ticket.last_client_message_at is None
        if ticket.status in OPEN_STATUSES and not ticket_rules.is_unread(
            ticket.last_client_message_at, ticket.staff_seen_at
        ):
            assert (
                ticket.last_client_message_at is None
                or ticket.staff_seen_at is None
                or ticket.staff_seen_at >= ticket.last_client_message_at
            )

    unread = [
        ticket
        for ticket in tickets
        if ticket.status in OPEN_STATUSES
        and ticket_rules.is_unread(ticket.last_client_message_at, ticket.staff_seen_at)
    ]
    assert 3 <= len(unread) <= 8


async def test_dashboard_over_generated_history(db: AsyncSession) -> None:
    now = datetime.now(UTC)
    await reset_demo(db, now=now, volume=0.3)
    await db.commit()

    dashboard = await DashboardService(db).get(30)
    assert dashboard.now.overdue >= 2
    assert dashboard.summary.created.value >= 30

    user_ids = await _demo_user_ids(db)
    recent_total = await db.scalar(
        select(func.count())
        .select_from(Ticket)
        .where(
            Ticket.client_id.in_(user_ids),
            Ticket.type == TicketType.REQUEST,
            Ticket.created_at >= now - timedelta(days=14),
        )
    )
    recent_heat = await db.scalar(
        select(func.count())
        .select_from(Ticket)
        .join(Category, Category.id == Ticket.category_id)
        .where(
            Ticket.client_id.in_(user_ids),
            Ticket.type == TicketType.REQUEST,
            Ticket.created_at >= now - timedelta(days=14),
            Category.title == "🔥 Отопление",
        )
    )
    older_total = await db.scalar(
        select(func.count())
        .select_from(Ticket)
        .where(
            Ticket.client_id.in_(user_ids),
            Ticket.type == TicketType.REQUEST,
            Ticket.created_at < now - timedelta(days=14),
            Ticket.created_at >= now - timedelta(days=60),
        )
    )
    older_heat = await db.scalar(
        select(func.count())
        .select_from(Ticket)
        .join(Category, Category.id == Ticket.category_id)
        .where(
            Ticket.client_id.in_(user_ids),
            Ticket.type == TicketType.REQUEST,
            Ticket.created_at < now - timedelta(days=14),
            Ticket.created_at >= now - timedelta(days=60),
            Category.title == "🔥 Отопление",
        )
    )
    assert recent_total and recent_heat
    recent_share = recent_heat / recent_total
    older_share = older_heat / older_total if older_total else 0
    assert recent_share >= 0.2
    assert recent_share > older_share * 3

    reacted = (
        select(
            Ticket.assignee_id,
            Ticket.created_at,
            func.min(StatusChange.created_at).label("reacted_at"),
        )
        .join(StatusChange, StatusChange.ticket_id == Ticket.id)
        .where(StatusChange.from_status == TicketStatus.NEW)
        .group_by(Ticket.id)
        .subquery()
    )
    rows = (
        await db.execute(
            select(
                User.first_name,
                func.avg(func.extract("epoch", reacted.c.reacted_at - reacted.c.created_at) / 60),
            )
            .join(User, User.id == reacted.c.assignee_id)
            .where(reacted.c.created_at >= now - timedelta(days=30))
            .group_by(User.first_name)
        )
    ).all()
    reaction = {name: float(value) for name, value in rows}
    assert reaction["Пётр"] > 1.5 * max(value for name, value in reaction.items() if name != "Пётр")


@pytest.mark.parametrize("title", ["🔥 Отопление"])
async def test_heating_requests_use_existing_category(db: AsyncSession, title: str) -> None:
    now = datetime.now(UTC)
    await reset_demo(db, now=now, volume=TEST_VOLUME)
    await db.commit()

    assert await db.scalar(select(Category).where(Category.title == title)) is not None
    addresses = set((await db.execute(select(Building.address))).scalars().all())
    demo_addresses = set(
        (
            await db.execute(
                select(Building.address)
                .join(Residence, Residence.building_id == Building.id)
                .join(User, User.id == Residence.user_id)
                .where(User.max_user_id >= DEMO_MAX_USER_ID_BASE)
            )
        )
        .scalars()
        .all()
    )
    # Core seed buildings plus the four invented ones.
    assert len(addresses) >= 8
    assert len(demo_addresses) >= 8


async def test_distribution_by_manager_and_category(db: AsyncSession) -> None:
    now = datetime.now(UTC)
    await reset_demo(db, now=now, volume=0.3)
    await db.commit()

    tickets = await _demo_tickets(db)
    by_manager: dict[int, int] = defaultdict(int)
    by_category: dict[str, int] = defaultdict(int)
    for ticket in tickets:
        if ticket.assignee_id is not None:
            by_manager[ticket.assignee_id] += 1
        if ticket.category is not None:
            by_category[ticket.category.title] += 1

    managers = await db.scalars(
        select(User).where(User.role == UserRole.MANAGER, User.max_user_id >= DEMO_MAX_USER_ID_BASE)
    )
    assert len(managers.all()) == 3
    assert sum(by_manager.values()) > 0
    assert len(by_category) == 7
