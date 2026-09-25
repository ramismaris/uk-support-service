from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import UserRole
from src.repositories.user_repository import UserRepository


async def test_get_by_max_user_id_returns_user(db: AsyncSession) -> None:
    repository = UserRepository(db)
    created = await repository.create(max_user_id=42, first_name="Иван", role=UserRole.MANAGER)

    found = await repository.get_by_max_user_id(42)

    assert found is not None
    assert found.id == created.id
    assert found.first_name == "Иван"
    assert found.role == UserRole.MANAGER


async def test_get_by_max_user_id_returns_none_when_missing(db: AsyncSession) -> None:
    repository = UserRepository(db)

    assert await repository.get_by_max_user_id(999) is None
