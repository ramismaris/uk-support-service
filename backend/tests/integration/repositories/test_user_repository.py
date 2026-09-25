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


async def test_list_staff_returns_active_managers_and_admins_ordered_by_id(
    db: AsyncSession,
) -> None:
    repository = UserRepository(db)
    await repository.create(max_user_id=1, first_name="Клиент")
    manager = await repository.create(max_user_id=2, first_name="Игорь", role=UserRole.MANAGER)
    admin = await repository.create(max_user_id=3, first_name="Анна", role=UserRole.ADMIN)
    blocked = await repository.create(max_user_id=4, first_name="Пётр", role=UserRole.MANAGER)
    blocked.is_blocked = True
    await db.commit()

    staff = await repository.list_staff()

    assert [user.id for user in staff] == [manager.id, admin.id]
    assert all(user.role in (UserRole.MANAGER, UserRole.ADMIN) for user in staff)
    assert all(not user.is_blocked for user in staff)


async def test_list_staff_returns_empty_when_no_staff(db: AsyncSession) -> None:
    repository = UserRepository(db)
    await repository.create(max_user_id=1, first_name="Клиент")
    await db.commit()

    assert await repository.list_staff() == []
