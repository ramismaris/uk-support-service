from datetime import UTC, datetime, timedelta
from itertools import pairwise

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from scripts.seed import seed
from src.core.constants import ContentKey, SenderType, TicketStatus, TicketType, UserRole
from src.models.building import Building
from src.models.category import Category
from src.models.content_block import ContentBlock
from src.models.message import Message
from src.models.residence import Residence
from src.models.status_change import StatusChange
from src.models.ticket import Ticket
from src.models.user import User
from src.repositories.content_block_repository import ContentBlockRepository
from src.repositories.message_repository import MessageRepository
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


LEAKY_DESCRIPTION = "Течёт кран на кухне, под раковиной лужа."
LIGHT_DESCRIPTION = "В подъезде на 3-м этаже не горит свет."
LIFT_DESCRIPTION = "Лифт останавливается между этажами, двери открываются не сразу."
GARBAGE_DESCRIPTION = "Не вывозят мусор у второго подъезда."
REJECTED_DESCRIPTION = "Прошу установить шлагбаум во дворе."
QUESTION_DESCRIPTION = "Когда будет перерасчёт за отопление за прошлый месяц?"

DEMO_MESSAGES_COUNT = 8


async def _ticket_by_description(db: AsyncSession, client: User, description: str) -> Ticket:
    ticket = await db.scalar(
        select(Ticket).where(Ticket.client_id == client.id, Ticket.description == description)
    )
    assert ticket is not None
    return ticket


async def test_seed_creates_demo_chats(db: AsyncSession) -> None:
    await seed(db)

    client = await UserRepository(db).get_by_max_user_id(1000003)
    manager = await UserRepository(db).get_by_max_user_id(1000002)
    assert client is not None
    assert manager is not None

    messages = MessageRepository(db)

    leaky = await _ticket_by_description(db, client, LEAKY_DESCRIPTION)
    chat = await messages.list_by_ticket(leaky.id)
    assert [message.text for message in chat] == [
        "Вода уже капает к соседям снизу, можно побыстрее?"
    ]
    assert chat[0].sender_type == SenderType.CLIENT
    assert chat[0].author_id == client.id
    assert chat[0].max_message_id is None
    assert chat[0].created_at == leaky.created_at + timedelta(minutes=30)
    assert leaky.last_client_message_at == leaky.created_at + timedelta(minutes=30)
    assert leaky.staff_seen_at is None

    light = await _ticket_by_description(db, client, LIGHT_DESCRIPTION)
    chat = await messages.list_by_ticket(light.id)
    assert [message.text for message in chat] == [
        "Здравствуйте! Электрик зайдёт сегодня до 18:00.",
        "Спасибо, буду ждать.",
    ]
    assert [message.sender_type for message in chat] == [SenderType.STAFF, SenderType.CLIENT]
    assert [message.author_id for message in chat] == [manager.id, client.id]
    assert chat[0].created_at == light.created_at + timedelta(minutes=30)
    assert chat[1].created_at == light.created_at + timedelta(hours=1)
    assert light.last_client_message_at == light.created_at + timedelta(hours=1)
    assert light.staff_seen_at == light.created_at + timedelta(hours=1, minutes=5)

    lift = await _ticket_by_description(db, client, LIFT_DESCRIPTION)
    chat = await messages.list_by_ticket(lift.id)
    assert [message.text for message in chat] == [
        "Здравствуйте! Передали заявку в лифтовую службу.",
        "Подскажите, пожалуйста, в каком подъезде этот лифт?",
    ]
    assert [message.sender_type for message in chat] == [SenderType.STAFF, SenderType.STAFF]
    assert [message.author_id for message in chat] == [manager.id, manager.id]
    assert lift.last_client_message_at is None
    assert lift.staff_seen_at is None

    garbage = await _ticket_by_description(db, client, GARBAGE_DESCRIPTION)
    chat = await messages.list_by_ticket(garbage.id)
    assert [message.text for message in chat] == [
        "Здравствуйте! Передали подрядчику, вывоз сегодня вечером.",
        "Всё вывезли, спасибо!",
        "Рады помочь! Закрываем заявку.",
    ]
    assert [message.sender_type for message in chat] == [
        SenderType.STAFF,
        SenderType.CLIENT,
        SenderType.STAFF,
    ]
    assert garbage.last_client_message_at == garbage.created_at + timedelta(days=1, hours=2)
    assert garbage.staff_seen_at == garbage.created_at + timedelta(days=2)

    rejected = await _ticket_by_description(db, client, REJECTED_DESCRIPTION)
    question = await _ticket_by_description(db, client, QUESTION_DESCRIPTION)
    assert await messages.list_by_ticket(rejected.id) == []
    assert await messages.list_by_ticket(question.id) == []

    assert await _count(db, Message) == DEMO_MESSAGES_COUNT


async def test_seed_demo_chats_are_idempotent(db: AsyncSession) -> None:
    await seed(db)
    assert await _count(db, Message) == DEMO_MESSAGES_COUNT

    await seed(db)

    assert await _count(db, Message) == DEMO_MESSAGES_COUNT


async def test_seed_adds_chats_to_existing_tickets_without_messages(db: AsyncSession) -> None:
    await seed(db)
    await db.execute(delete(Message))
    for ticket in (await db.execute(select(Ticket))).scalars().all():
        ticket.last_client_message_at = None
        ticket.staff_seen_at = None
    await db.flush()
    assert await _count(db, Message) == 0

    await seed(db)

    assert await _count(db, Message) == DEMO_MESSAGES_COUNT
