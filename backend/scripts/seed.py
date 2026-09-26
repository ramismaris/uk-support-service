"""Idempotent demo seed for the UK support service.

Run from backend/: uv run python scripts/seed.py
"""

import asyncio
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import ContentKey, SenderType, TicketStatus, TicketType, UserRole
from src.db.session import AsyncSessionLocal
from src.models.building import Building
from src.models.category import Category
from src.models.content_block import ContentBlock
from src.models.message import Message
from src.models.ticket import Ticket
from src.models.user import User
from src.repositories.building_repository import BuildingRepository
from src.repositories.category_repository import CategoryRepository
from src.repositories.content_block_repository import ContentBlockRepository
from src.repositories.message_repository import MessageRepository
from src.repositories.residence_repository import ResidenceRepository
from src.repositories.status_change_repository import StatusChangeRepository
from src.repositories.ticket_repository import TicketRepository
from src.repositories.user_repository import UserRepository

BUILDINGS = [
    "ул. Ленина, 12",
    "ул. Гагарина, 5",
    "пр-т Мира, 28",
    "ул. Садовая, 7",
]

CATEGORIES = [
    "Сантехника",
    "Электрика",
    "Лифт",
    "Уборка",
    "Благоустройство",
    "Другое",
]

DEMO_CLIENT_MAX_USER_ID = 1000003
DEMO_MANAGER_MAX_USER_ID = 1000002
DEMO_PHONE = "+7 (900) 000-00-03"
DEMO_BUILDING = "ул. Ленина, 12"
DEMO_APARTMENT = "45"

USERS = [
    {
        "max_user_id": 1000001,
        "first_name": "Анна",
        "last_name": "Петрова",
        "username": "demo_admin",
        "role": UserRole.ADMIN,
    },
    {
        "max_user_id": 1000002,
        "first_name": "Игорь",
        "last_name": "Смирнов",
        "username": "demo_manager",
        "role": UserRole.MANAGER,
    },
    {
        "max_user_id": 1000003,
        "first_name": "Мария",
        "last_name": "Иванова",
        "username": "demo_client",
        "role": UserRole.CLIENT,
        "phone": DEMO_PHONE,
    },
]

CONTENT_BLOCKS = {
    ContentKey.WELCOME: {
        "text": (
            "Здравствуйте! Это бот управляющей компании «Наш дом». "
            "Здесь можно подать заявку, задать вопрос и следить за её статусом."
        ),
        "file_id": None,
    },
    ContentKey.EMERGENCY: {
        "text": (
            "Аварийная служба работает круглосуточно. "
            "При аварии звоните: +7 (800) 000-00-02. "
            "Если есть угроза жизни и здоровью, не ждите ответа в боте."
        )
    },
    ContentKey.SERVICES: {
        "text": (
            "Мы отвечаем за содержание и ремонт общего имущества, "
            "уборку подъездов и придомовой территории, "
            "обслуживание лифтов и инженерных систем."
        )
    },
    ContentKey.PAYMENT: {
        "text": (
            "Оплатить жилищно-коммунальные услуги можно по кнопке ниже. "
            "Квитанция приходит до 1-го числа каждого месяца."
        ),
        "url": "https://example.com/payment",
        "button_text": "Оплатить ЖКХ",
    },
    ContentKey.CONTACTS: {
        "text": "Свяжитесь с нами удобным способом. В рабочее время отвечаем и в боте.",
        "phones": [
            {"title": "Диспетчерская", "phone": "+7 (800) 000-00-01"},
            {"title": "Аварийная служба", "phone": "+7 (800) 000-00-02"},
        ],
    },
    ContentKey.THEME: {
        "company_name": "УК «Наш дом»",
        "primary_color": "#1E88E5",
        "logo_file_id": None,
    },
}


DEMO_CHATS: list[dict] = [
    {
        "description": "Течёт кран на кухне, под раковиной лужа.",
        "messages": [
            {
                "sender": SenderType.CLIENT,
                "text": "Вода уже капает к соседям снизу, можно побыстрее?",
                "offset": timedelta(minutes=30),
            },
        ],
        "last_client_message_at_offset": timedelta(minutes=30),
        "staff_seen_at_offset": None,
    },
    {
        "description": "В подъезде на 3-м этаже не горит свет.",
        "messages": [
            {
                "sender": SenderType.STAFF,
                "text": "Здравствуйте! Электрик зайдёт сегодня до 18:00.",
                "offset": timedelta(minutes=30),
            },
            {
                "sender": SenderType.CLIENT,
                "text": "Спасибо, буду ждать.",
                "offset": timedelta(hours=1),
            },
        ],
        "last_client_message_at_offset": timedelta(hours=1),
        "staff_seen_at_offset": timedelta(hours=1, minutes=5),
    },
    {
        "description": "Лифт останавливается между этажами, двери открываются не сразу.",
        "messages": [
            {
                "sender": SenderType.STAFF,
                "text": "Здравствуйте! Передали заявку в лифтовую службу.",
                "offset": timedelta(hours=1),
            },
            {
                "sender": SenderType.STAFF,
                "text": "Подскажите, пожалуйста, в каком подъезде этот лифт?",
                "offset": timedelta(days=1),
            },
        ],
        "last_client_message_at_offset": None,
        "staff_seen_at_offset": None,
    },
    {
        "description": "Не вывозят мусор у второго подъезда.",
        "messages": [
            {
                "sender": SenderType.STAFF,
                "text": "Здравствуйте! Передали подрядчику, вывоз сегодня вечером.",
                "offset": timedelta(hours=2),
            },
            {
                "sender": SenderType.CLIENT,
                "text": "Всё вывезли, спасибо!",
                "offset": timedelta(days=1, hours=2),
            },
            {
                "sender": SenderType.STAFF,
                "text": "Рады помочь! Закрываем заявку.",
                "offset": timedelta(days=2) - timedelta(minutes=10),
            },
        ],
        "last_client_message_at_offset": timedelta(days=1, hours=2),
        "staff_seen_at_offset": timedelta(days=2),
    },
]


async def seed(db: AsyncSession) -> None:
    users = UserRepository(db)
    for spec in USERS:
        if await users.get_by_max_user_id(spec["max_user_id"]) is None:
            await users.create(**spec)

    buildings = BuildingRepository(db)
    for address in BUILDINGS:
        if await buildings.get_by_address(address) is None:
            await buildings.create(address)

    categories = CategoryRepository(db)
    for sort_order, title in enumerate(CATEGORIES, start=1):
        if await categories.get_by_title(title) is None:
            await categories.create(title, sort_order)

    content = ContentBlockRepository(db)
    for key, data in CONTENT_BLOCKS.items():
        if await content.get(key) is None:
            await content.create(key, data)

    client = await users.get_by_max_user_id(DEMO_CLIENT_MAX_USER_ID)
    manager = await users.get_by_max_user_id(DEMO_MANAGER_MAX_USER_ID)
    building = await buildings.get_by_address(DEMO_BUILDING)

    residences = ResidenceRepository(db)
    if await residences.get(client.id, building.id, DEMO_APARTMENT) is None:
        await residences.create(client.id, building.id, DEMO_APARTMENT, is_primary=True)

    has_tickets = await db.scalar(
        select(func.count()).select_from(Ticket).where(Ticket.client_id == client.id)
    )
    if not has_tickets:
        await _seed_demo_tickets(db, client, manager, building, categories)

    await _seed_demo_chats(db, client, manager)


async def _seed_demo_tickets(
    db: AsyncSession,
    client: User,
    manager: User,
    building: Building,
    categories: CategoryRepository,
) -> None:
    now = datetime.now(UTC)
    tickets = TicketRepository(db)
    history = StatusChangeRepository(db)

    specs: list[dict] = [
        {
            "type": TicketType.REQUEST,
            "status": TicketStatus.NEW,
            "category": "Сантехника",
            "created_at": now - timedelta(minutes=40),
            "description": "Течёт кран на кухне, под раковиной лужа.",
            "preferred_time": "Будни после 18:00",
            "transitions": [],
        },
        {
            "type": TicketType.REQUEST,
            "status": TicketStatus.IN_PROGRESS,
            "category": "Электрика",
            "created_at": now - timedelta(days=1),
            "description": "В подъезде на 3-м этаже не горит свет.",
            "assignee": manager,
            "transitions": [
                {
                    "to_status": TicketStatus.IN_PROGRESS,
                    "at": now - timedelta(days=1) + timedelta(minutes=30),
                },
            ],
        },
        {
            "type": TicketType.REQUEST,
            "status": TicketStatus.WAITING_CLIENT,
            "category": "Лифт",
            "created_at": now - timedelta(days=2),
            "description": "Лифт останавливается между этажами, двери открываются не сразу.",
            "assignee": manager,
            "transitions": [
                {
                    "to_status": TicketStatus.IN_PROGRESS,
                    "at": now - timedelta(days=2) + timedelta(hours=1),
                },
                {"to_status": TicketStatus.WAITING_CLIENT, "at": now - timedelta(days=1)},
            ],
        },
        {
            "type": TicketType.REQUEST,
            "status": TicketStatus.CLOSED,
            "category": "Уборка",
            "created_at": now - timedelta(days=5),
            "description": "Не вывозят мусор у второго подъезда.",
            "assignee": manager,
            "rating": 5,
            "transitions": [
                {
                    "to_status": TicketStatus.IN_PROGRESS,
                    "at": now - timedelta(days=5) + timedelta(hours=2),
                },
                {"to_status": TicketStatus.CLOSED, "at": now - timedelta(days=3)},
            ],
        },
        {
            "type": TicketType.REQUEST,
            "status": TicketStatus.REJECTED,
            "category": "Благоустройство",
            "created_at": now - timedelta(days=6),
            "description": "Прошу установить шлагбаум во дворе.",
            "transitions": [
                {
                    "to_status": TicketStatus.REJECTED,
                    "at": now - timedelta(days=5),
                    "comment": ("Установка шлагбаума решается общим собранием собственников."),
                },
            ],
        },
        {
            "type": TicketType.QUESTION,
            "status": TicketStatus.NEW,
            "category": None,
            "created_at": now - timedelta(hours=3),
            "description": "Когда будет перерасчёт за отопление за прошлый месяц?",
            "has_address": False,
            "transitions": [],
        },
    ]

    for spec in specs:
        category = None
        if spec["category"] is not None:
            category = await categories.get_by_title(spec["category"])
        assignee = spec.get("assignee")
        has_address = spec.get("has_address", True)
        transitions: list[dict] = spec["transitions"]
        closed_at = (
            transitions[-1]["at"]
            if spec["status"]
            in (
                TicketStatus.CLOSED,
                TicketStatus.REJECTED,
            )
            else None
        )

        ticket = await tickets.create(
            type=spec["type"],
            status=spec["status"],
            client_id=client.id,
            description=spec["description"],
            category_id=category.id if category else None,
            building_id=building.id if has_address else None,
            apartment=DEMO_APARTMENT if has_address else None,
            contact_phone=DEMO_PHONE,
            preferred_time=spec.get("preferred_time"),
            assignee_id=assignee.id if assignee else None,
            rating=spec.get("rating"),
            created_at=spec["created_at"],
            closed_at=closed_at,
        )

        rows = [{"to_status": TicketStatus.NEW, "at": spec["created_at"]}, *transitions]
        previous_status = None
        for index, row in enumerate(rows):
            await history.create(
                ticket.id,
                previous_status,
                row["to_status"],
                changed_by_id=client.id if index == 0 else manager.id,
                comment=row.get("comment"),
                created_at=row["at"],
            )
            previous_status = row["to_status"]


async def _seed_demo_chats(db: AsyncSession, client: User, manager: User) -> None:
    has_messages = await db.scalar(
        select(func.count())
        .select_from(Message)
        .join(Ticket, Message.ticket_id == Ticket.id)
        .where(Ticket.client_id == client.id)
    )
    if has_messages:
        return

    messages = MessageRepository(db)
    for spec in DEMO_CHATS:
        ticket = await db.scalar(
            select(Ticket).where(
                Ticket.client_id == client.id,
                Ticket.description == spec["description"],
            )
        )
        if ticket is None:
            continue

        for message_spec in spec["messages"]:
            is_staff = message_spec["sender"] == SenderType.STAFF
            await messages.create(
                ticket.id,
                message_spec["sender"],
                author_id=manager.id if is_staff else client.id,
                text=message_spec["text"],
                created_at=ticket.created_at + message_spec["offset"],
            )

        last_client_message_offset = spec["last_client_message_at_offset"]
        if last_client_message_offset is not None:
            ticket.last_client_message_at = ticket.created_at + last_client_message_offset
        staff_seen_offset = spec["staff_seen_at_offset"]
        if staff_seen_offset is not None:
            ticket.staff_seen_at = ticket.created_at + staff_seen_offset
    await db.flush()


async def _count_rows(db: AsyncSession) -> dict[str, int]:
    counts: dict[str, int] = {}
    for name, model in {
        "buildings": Building,
        "categories": Category,
        "content_blocks": ContentBlock,
        "users": User,
        "tickets": Ticket,
    }.items():
        counts[name] = await db.scalar(select(func.count()).select_from(model)) or 0
    return counts


async def main() -> None:
    async with AsyncSessionLocal() as db:
        before = await _count_rows(db)
        await seed(db)
        await db.commit()
        after = await _count_rows(db)

    added = {name: after[name] - before[name] for name in after}
    print(
        "Добавлено: "
        f"дома — {added['buildings']}, "
        f"категории — {added['categories']}, "
        f"блоки контента — {added['content_blocks']}, "
        f"пользователи — {added['users']}, "
        f"обращения — {added['tickets']}."
    )


if __name__ == "__main__":
    asyncio.run(main())
