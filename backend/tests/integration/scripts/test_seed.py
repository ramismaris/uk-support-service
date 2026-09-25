from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from scripts.seed import seed
from src.core.constants import ContentKey, UserRole
from src.models.building import Building
from src.models.category import Category
from src.models.content_block import ContentBlock
from src.models.user import User
from src.repositories.content_block_repository import ContentBlockRepository

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
