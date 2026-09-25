"""Idempotent demo seed for the UK support service.

Run from backend/: uv run python scripts/seed.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import ContentKey, UserRole
from src.db.session import AsyncSessionLocal
from src.models.building import Building
from src.models.category import Category
from src.models.content_block import ContentBlock
from src.models.user import User
from src.repositories.building_repository import BuildingRepository
from src.repositories.category_repository import CategoryRepository
from src.repositories.content_block_repository import ContentBlockRepository
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


async def _count_rows(db: AsyncSession) -> dict[str, int]:
    counts: dict[str, int] = {}
    for name, model in {
        "buildings": Building,
        "categories": Category,
        "content_blocks": ContentBlock,
        "users": User,
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
        f"пользователи — {added['users']}."
    )


if __name__ == "__main__":
    asyncio.run(main())
