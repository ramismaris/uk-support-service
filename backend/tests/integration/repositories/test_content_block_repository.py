from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import ContentKey
from src.repositories.content_block_repository import ContentBlockRepository


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
