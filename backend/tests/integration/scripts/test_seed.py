from datetime import UTC, datetime
from itertools import pairwise

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from scripts.seed import seed
from src.core.constants import ContentKey, TicketStatus, TicketType, UserRole
from src.models.building import Building
from src.models.category import Category
from src.models.content_block import ContentBlock
from src.models.residence import Residence
from src.models.status_change import StatusChange
from src.models.ticket import Ticket
from src.models.user import User
from src.repositories.content_block_repository import ContentBlockRepository
from src.repositories.status_change_repository import StatusChangeRepository
from src.repositories.user_repository import UserRepository
from src.services import ticket_rules

EXPECTED_CATEGORIES = [
    "Сантехника",
    "Электрика",
    "Лифт",
    "Уборка",
    "Благоустройство",
    "Другое",
]


async def _count(db: AsyncSession, model: type) -> int:
    return await db.scalar(select(func.count()).select_from(model)) or 0


async def test_seed_creates_demo_data(db: AsyncSession) -> None:
    await seed(db)

    assert await _count(db, Building) == 4
    assert await _count(db, Category) == 6
    assert await _count(db, ContentBlock) == 6
    assert await _count(db, User) == 3

    categories = (await db.execute(select(Category).order_by(Category.sort_order))).scalars().all()
    assert [category.title for category in categories] == EXPECTED_CATEGORIES
    assert [category.sort_order for category in categories] == [1, 2, 3, 4, 5, 6]

    users = (await db.execute(select(User))).scalars().all()
    assert {user.role for user in users} == {UserRole.ADMIN, UserRole.MANAGER, UserRole.CLIENT}
    assert {user.max_user_id for user in users} == {1000001, 1000002, 1000003}

    blocks = (await db.execute(select(ContentBlock))).scalars().all()
    assert {block.key for block in blocks} == {key.value for key in ContentKey}


async def test_seed_is_idempotent(db: AsyncSession) -> None:
    await seed(db)
    await seed(db)

    assert await _count(db, Building) == 4
    assert await _count(db, Category) == 6
    assert await _count(db, ContentBlock) == 6
    assert await _count(db, User) == 3


async def test_seed_does_not_overwrite_changed_content(db: AsyncSession) -> None:
    await seed(db)
    repository = ContentBlockRepository(db)
    block = await repository.get(ContentKey.WELCOME)
    assert block is not None
    block.data = {"text": "Изменено администратором", "file_id": None}
    await db.flush()

    await seed(db)

    updated = await repository.get(ContentKey.WELCOME)
    assert updated is not None
    assert updated.data == {"text": "Изменено администратором", "file_id": None}


async def test_seed_creates_demo_tickets(db: AsyncSession) -> None:
    await seed(db)

    client = await UserRepository(db).get_by_max_user_id(1000003)
    manager = await UserRepository(db).get_by_max_user_id(1000002)
    assert client is not None
    assert manager is not None

    tickets = (await db.execute(select(Ticket).order_by(Ticket.created_at))).scalars().all()
    assert len(tickets) == 6
    assert {ticket.status for ticket in tickets} == set(TicketStatus)

    changes = StatusChangeRepository(db)
    for ticket in tickets:
        history = await changes.list_by_ticket(ticket.id)
        assert history, ticket.id
        assert history[0].from_status is None
        assert history[0].to_status == TicketStatus.NEW
        assert history[0].changed_by_id == client.id
        assert history[-1].to_status == ticket.status
        for previous, current in pairwise(history):
            assert current.from_status == previous.to_status

        for index, change in enumerate(history):
            if index == 0:
                continue
            assert change.changed_by_id == manager.id
            ticket_rules.check_transition(
                history[index - 1].to_status,
                change.to_status,
                UserRole.MANAGER,
                closed_at=ticket.closed_at,
                now=datetime.now(UTC),
            )

        if ticket.status in (TicketStatus.CLOSED, TicketStatus.REJECTED):
            assert ticket.closed_at is not None
            assert ticket.closed_at == history[-1].created_at
        else:
            assert ticket.closed_at is None

    closed = next(ticket for ticket in tickets if ticket.status == TicketStatus.CLOSED)
    assert closed.rating == 5

    rejected = next(ticket for ticket in tickets if ticket.status == TicketStatus.REJECTED)
    rejected_history = await changes.list_by_ticket(rejected.id)
    assert rejected_history[-1].comment == (
        "Установка шлагбаума решается общим собранием собственников."
    )

    question = next(ticket for ticket in tickets if ticket.type == TicketType.QUESTION)
    assert question.category_id is None
    assert question.building_id is None
    assert question.apartment is None


async def test_seed_creates_primary_residence(db: AsyncSession) -> None:
    await seed(db)

    client = await UserRepository(db).get_by_max_user_id(1000003)
    assert client is not None

    residences = (
        (await db.execute(select(Residence).where(Residence.user_id == client.id))).scalars().all()
    )
    assert len(residences) == 1
    assert residences[0].apartment == "45"
    assert residences[0].is_primary is True


async def test_seed_tickets_are_idempotent(db: AsyncSession) -> None:
    await seed(db)
    tickets_before = await _count(db, Ticket)
    history_before = await _count(db, StatusChange)
    residences_before = await _count(db, Residence)

    await seed(db)

    assert await _count(db, Ticket) == tickets_before
    assert await _count(db, StatusChange) == history_before
    assert await _count(db, Residence) == residences_before
