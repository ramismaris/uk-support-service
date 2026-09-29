from datetime import UTC, datetime
from unittest.mock import AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import UserRole
from src.repositories.building_repository import BuildingRepository
from src.repositories.residence_repository import ResidenceRepository
from src.repositories.user_repository import UserRepository


async def test_list_by_ids_returns_found_and_skips_missing(db: AsyncSession) -> None:
    repository = UserRepository(db)
    first = await repository.create(max_user_id=1, first_name="Иван")
    second = await repository.create(max_user_id=2, first_name="Пётр")
    await repository.create(max_user_id=3, first_name="Олег")
    await db.commit()

    found = await repository.list_by_ids([first.id, second.id, 999999])

    assert {user.id for user in found} == {first.id, second.id}


async def test_list_by_ids_with_empty_input_does_not_query() -> None:
    db = AsyncMock(spec=AsyncSession)
    repository = UserRepository(db)

    assert await repository.list_by_ids([]) == []

    db.execute.assert_not_awaited()


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


async def _seen(user):
    user.last_seen_at = datetime.now(UTC)
    return user


async def test_list_broadcast_recipients_includes_only_seen_clients_ordered_by_id(
    db: AsyncSession,
) -> None:
    repository = UserRepository(db)
    first = await _seen(await _create(db, repository, max_user_id=200, first_name="Первый"))
    second = await _seen(await _create(db, repository, max_user_id=100, first_name="Второй"))
    await _create(db, repository, max_user_id=1, first_name="Молчун")
    blocked = await _seen(
        await _create(db, repository, max_user_id=2, first_name="Блок", is_blocked=True)
    )
    manager = await _seen(
        await _create(db, repository, max_user_id=3, first_name="Мен", role=UserRole.MANAGER)
    )
    admin = await _seen(
        await _create(db, repository, max_user_id=4, first_name="Адм", role=UserRole.ADMIN)
    )
    await db.commit()

    recipients = await repository.list_broadcast_recipients(None)

    # Ordered by users.id, not by max_user_id: first was created before second.
    assert recipients == [first.max_user_id, second.max_user_id]
    assert blocked.max_user_id not in recipients
    assert manager.max_user_id not in recipients
    assert admin.max_user_id not in recipients


async def test_list_broadcast_recipients_by_buildings_deduplicates(db: AsyncSession) -> None:
    repository = UserRepository(db)
    buildings = BuildingRepository(db)
    chosen_a = await buildings.create("ул. А, 1")
    chosen_b = await buildings.create("ул. Б, 1")
    other = await buildings.create("ул. В, 1")

    residents = ResidenceRepository(db)
    in_a = await _seen(await _create(db, repository, max_user_id=11, first_name="Аня"))
    await residents.create(in_a.id, chosen_a.id, "1")
    out = await _seen(await _create(db, repository, max_user_id=12, first_name="Олег"))
    await residents.create(out.id, other.id, "1")
    both = await _seen(await _create(db, repository, max_user_id=13, first_name="Борис"))
    await residents.create(both.id, chosen_a.id, "1")
    await residents.create(both.id, chosen_b.id, "2")
    await db.commit()

    recipients = await repository.list_broadcast_recipients([chosen_a.id, chosen_b.id])

    assert recipients == [in_a.max_user_id, both.max_user_id]
    assert out.max_user_id not in recipients


async def test_list_broadcast_recipients_by_building_needs_a_residence(
    db: AsyncSession,
) -> None:
    repository = UserRepository(db)
    building = await BuildingRepository(db).create("ул. А, 1")
    seen = await _seen(await _create(db, repository, max_user_id=21, first_name="Аня"))
    await db.commit()

    assert await repository.list_broadcast_recipients([building.id]) == []
    assert await repository.list_broadcast_recipients(None) == [seen.max_user_id]


async def test_list_broadcast_recipients_empty_buildings_returns_nobody(
    db: AsyncSession,
) -> None:
    repository = UserRepository(db)
    await _seen(await _create(db, repository, max_user_id=31, first_name="Аня"))
    await db.commit()

    assert await repository.list_broadcast_recipients([]) == []
