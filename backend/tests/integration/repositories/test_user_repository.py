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


async def _create(
    db: AsyncSession,
    repository: UserRepository,
    *,
    max_user_id: int,
    first_name: str,
    last_name: str | None = None,
    username: str | None = None,
    phone: str | None = None,
    role: UserRole = UserRole.CLIENT,
    is_blocked: bool = False,
):
    user = await repository.create(
        max_user_id=max_user_id,
        first_name=first_name,
        last_name=last_name,
        username=username,
        phone=phone,
        role=role,
    )
    user.is_blocked = is_blocked
    return user


async def test_list_filters_by_roles(db: AsyncSession) -> None:
    repository = UserRepository(db)
    await _create(db, repository, max_user_id=1, first_name="Клиент")
    manager = await _create(
        db, repository, max_user_id=2, first_name="Игорь", role=UserRole.MANAGER
    )
    admin = await _create(db, repository, max_user_id=3, first_name="Анна", role=UserRole.ADMIN)
    await db.commit()

    found = await repository.list(roles=[UserRole.MANAGER, UserRole.ADMIN])

    assert {user.id for user in found} == {manager.id, admin.id}


async def test_list_filters_by_is_blocked(db: AsyncSession) -> None:
    repository = UserRepository(db)
    await _create(db, repository, max_user_id=1, first_name="Клиент")
    blocked = await _create(
        db, repository, max_user_id=2, first_name="Пётр", role=UserRole.MANAGER, is_blocked=True
    )
    await db.commit()

    found = await repository.list(is_blocked=True)

    assert [user.id for user in found] == [blocked.id]


async def test_list_search_matches_name_username_and_phone_case_insensitively(
    db: AsyncSession,
) -> None:
    repository = UserRepository(db)
    by_first = await _create(db, repository, max_user_id=1, first_name="Иван", last_name="Петров")
    by_last = await _create(db, repository, max_user_id=2, first_name="Сергей", last_name="Иванов")
    by_username = await _create(
        db, repository, max_user_id=3, first_name="Анна", username="ivan_work"
    )
    by_phone = await _create(
        db, repository, max_user_id=4, first_name="Мария", phone="+7 (900) 111-22-33"
    )
    await _create(db, repository, max_user_id=5, first_name="Олег")
    await db.commit()

    assert {u.id for u in await repository.list(search="ИВАН")} == {by_first.id, by_last.id}
    assert {u.id for u in await repository.list(search="Иван Петров")} == {by_first.id}
    assert {u.id for u in await repository.list(search="ivan_wo")} == {by_username.id}
    assert {u.id for u in await repository.list(search="111-22")} == {by_phone.id}


async def test_list_search_matches_percent_and_underscore_literally(db: AsyncSession) -> None:
    repository = UserRepository(db)
    with_percent = await _create(db, repository, max_user_id=1, first_name="100% Иван")
    with_underscore = await _create(db, repository, max_user_id=2, first_name="Иван_Петров")
    await _create(db, repository, max_user_id=3, first_name="Иван Петров")
    await db.commit()

    assert [u.id for u in await repository.list(search="100%")] == [with_percent.id]
    assert [u.id for u in await repository.list(search="Иван_")] == [with_underscore.id]


async def test_list_max_user_id_is_ored_with_search(db: AsyncSession) -> None:
    repository = UserRepository(db)
    by_id = await _create(db, repository, max_user_id=1000003, first_name="Мария")
    by_search = await _create(db, repository, max_user_id=2, first_name="Мария Другая")
    await _create(db, repository, max_user_id=3, first_name="Олег")
    await db.commit()

    found = await repository.list(search="Мария", max_user_id=1000003)

    assert {u.id for u in found} == {by_id.id, by_search.id}


async def test_list_count_is_total_without_paging(db: AsyncSession) -> None:
    repository = UserRepository(db)
    for i in range(3):
        await _create(db, repository, max_user_id=100 + i, first_name=f"Иван{i}")
    await db.commit()

    total = await repository.count()
    page = await repository.list(skip=0, limit=2)

    assert total == 3
    assert len(page) == 2


async def test_list_orders_by_id_desc_and_pages(db: AsyncSession) -> None:
    repository = UserRepository(db)
    first = await _create(db, repository, max_user_id=1, first_name="Первый")
    second = await _create(db, repository, max_user_id=2, first_name="Второй")
    third = await _create(db, repository, max_user_id=3, first_name="Третий")
    await db.commit()

    page_one = await repository.list(skip=0, limit=2)
    page_two = await repository.list(skip=2, limit=2)

    assert [u.id for u in page_one] == [third.id, second.id]
    assert [u.id for u in page_two] == [first.id]
