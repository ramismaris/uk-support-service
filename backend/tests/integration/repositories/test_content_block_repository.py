from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import ContentKey, UserRole
from src.repositories.content_block_repository import ContentBlockRepository
from src.repositories.user_repository import UserRepository


async def test_get_returns_none_for_missing_key(db: AsyncSession) -> None:
    repository = ContentBlockRepository(db)

    assert await repository.get(ContentKey.WELCOME) is None


async def test_create_and_get_returns_block(db: AsyncSession) -> None:
    repository = ContentBlockRepository(db)
    data = {"text": "Здравствуйте", "file_id": None}
    created = await repository.create(ContentKey.WELCOME, data)

    found = await repository.get(ContentKey.WELCOME)

    assert created.key == ContentKey.WELCOME
    assert found is not None
    assert found.data == data


async def test_list_all_orders_by_key(db: AsyncSession) -> None:
    repository = ContentBlockRepository(db)
    await repository.create(ContentKey.SERVICES, {"text": "Услуги"})
    await repository.create(ContentKey.EMERGENCY, {"text": "Аварийные службы"})

    blocks = await repository.list_all()

    assert [block.key for block in blocks] == [ContentKey.EMERGENCY, ContentKey.SERVICES]


async def _create_admin(db: AsyncSession) -> int:
    user = await UserRepository(db).create(
        max_user_id=999001, first_name="Анна", role=UserRole.ADMIN
    )
    await db.commit()
    return user.id


async def test_upsert_inserts_missing_key(db: AsyncSession) -> None:
    repository = ContentBlockRepository(db)
    admin_id = await _create_admin(db)
    data = {"text": "Здравствуйте", "file_id": None}

    await repository.upsert(ContentKey.WELCOME, data, updated_by_id=admin_id)
    await db.commit()

    found = await repository.get(ContentKey.WELCOME)

    assert found is not None
    assert found.data == data
    assert found.updated_by_id == admin_id
    assert found.updated_at is not None


async def test_upsert_updates_existing_key(db: AsyncSession) -> None:
    repository = ContentBlockRepository(db)
    admin_id = await _create_admin(db)
    await repository.create(ContentKey.WELCOME, {"text": "Старое", "file_id": None})
    await db.commit()

    block = await repository.get(ContentKey.WELCOME)
    assert block is not None
    block.data = {"text": "Старое", "file_id": None}
    block.updated_by_id = None
    block.updated_at = datetime(2020, 1, 1, tzinfo=UTC)
    await db.commit()

    await repository.upsert(
        ContentKey.WELCOME, {"text": "Новое", "file_id": None}, updated_by_id=admin_id
    )
    await db.commit()
    db.expire_all()

    updated = await repository.get(ContentKey.WELCOME)

    assert updated is not None
    assert updated.data == {"text": "Новое", "file_id": None}
    assert updated.updated_by_id == admin_id
    assert updated.updated_at > datetime(2020, 1, 1, tzinfo=UTC)
