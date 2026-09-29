from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import (
    DIRECTORY_ACTIVE_LIMIT,
    TicketStatus,
    TicketType,
    UserRole,
)
from src.core.security import hash_token
from src.core.texts import (
    BUILDING_EXISTS,
    BUILDING_LAST_ACTIVE,
    BUILDINGS_LIMIT,
    CATEGORIES_LIMIT,
    CATEGORY_EXISTS,
    CATEGORY_LAST_ACTIVE,
    CATEGORY_ORDER_STALE,
)
from src.repositories.auth_token_repository import AuthTokenRepository
from src.repositories.building_repository import BuildingRepository
from src.repositories.category_repository import CategoryRepository
from src.repositories.ticket_repository import TicketRepository
from src.repositories.user_repository import UserRepository

ADMIN_BUILDINGS = "/api/v1/admin/buildings"
ADMIN_CATEGORIES = "/api/v1/admin/categories"
ADMIN_ORDER = "/api/v1/admin/categories/order"
STAFF_BUILDINGS = "/api/v1/staff/buildings"
STAFF_CATEGORIES = "/api/v1/staff/categories"
NOW = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _issue_token(db: AsyncSession, user, label: str) -> str:
    token = f"directory-token-{user.id}-{label}"
    await AuthTokenRepository(db).create(
        user.id, hash_token(token), datetime.now(UTC) + timedelta(days=1)
    )
    return token


@pytest.fixture
async def base(db: AsyncSession) -> SimpleNamespace:
    users = UserRepository(db)
    client = await users.create(max_user_id=2000003, first_name="Мария")
    manager = await users.create(max_user_id=2000002, first_name="Игорь", role=UserRole.MANAGER)
    admin = await users.create(max_user_id=2000001, first_name="Анна", role=UserRole.ADMIN)

    buildings = BuildingRepository(db)
    building_a = await buildings.create("ул. А, 1")
    building_b = await buildings.create("ул. Б, 1")

    categories = CategoryRepository(db)
    category_a = await categories.create("Сантехника", 1)
    category_b = await categories.create("Электрика", 2)

    client_token = await _issue_token(db, client, "live")
    manager_token = await _issue_token(db, manager, "live")
    admin_token = await _issue_token(db, admin, "live")
    await db.commit()

    return SimpleNamespace(
        client=client,
        manager=manager,
        admin=admin,
        building_a=building_a,
        building_b=building_b,
        category_a=category_a,
        category_b=category_b,
        client_token=client_token,
        manager_token=manager_token,
        admin_token=admin_token,
    )


async def _fill_buildings(db: AsyncSession, count: int, *, active: bool = True) -> None:
    repository = BuildingRepository(db)
    start = len(await repository.list_all())
    for index in range(count):
        building = await repository.create(f"доп. дом {start + index}")
        if not active:
            building.is_active = False
    await db.commit()


async def _fill_categories(db: AsyncSession, count: int, *, active: bool = True) -> None:
    repository = CategoryRepository(db)
    start = len(await repository.list_all())
    next_order = await repository.max_sort_order() + 1
    for index in range(count):
        category = await repository.create(f"Доп. категория {start + index}", next_order + index)
        if not active:
            category.is_active = False
    await db.commit()


async def _create_ticket(db: AsyncSession, base: SimpleNamespace, building) -> int:
    ticket = await TicketRepository(db).create(
        type=TicketType.REQUEST,
        status=TicketStatus.NEW,
        client_id=base.client.id,
        description="Протечка",
        building_id=building.id,
        category_id=base.category_a.id,
        apartment="12",
        created_at=NOW,
    )
    await db.commit()
    return ticket.id


async def _call(client: AsyncClient, method: str, path: str, *, headers=None, body=None):
    return await client.request(method, path, json=body, headers=headers)


ADMIN_ROUTES = [
    pytest.param("GET", ADMIN_BUILDINGS, None, id="buildings-list"),
    pytest.param("POST", ADMIN_BUILDINGS, {"address": "ул. А, 1"}, id="buildings-create"),
    pytest.param("PATCH", f"{ADMIN_BUILDINGS}/1", {"address": "ул. А, 2"}, id="buildings-patch"),
    pytest.param("GET", ADMIN_CATEGORIES, None, id="categories-list"),
    pytest.param("POST", ADMIN_CATEGORIES, {"title": "Прочее"}, id="categories-create"),
    pytest.param("PUT", ADMIN_ORDER, {"ids": [1]}, id="categories-order"),
    pytest.param("PATCH", f"{ADMIN_CATEGORIES}/1", {"title": "Прочее"}, id="categories-patch"),
]


@pytest.mark.parametrize(("method", "path", "body"), ADMIN_ROUTES)
async def test_admin_routes_require_token(
    client: AsyncClient, method: str, path: str, body: dict | None
) -> None:
    resp = await _call(client, method, path, body=body)

    assert resp.status_code == 401


@pytest.mark.parametrize("role", ["client", "manager"])
@pytest.mark.parametrize(("method", "path", "body"), ADMIN_ROUTES)
async def test_admin_routes_forbidden_for_non_admin(
    client: AsyncClient,
    base: SimpleNamespace,
    role: str,
    method: str,
    path: str,
    body: dict | None,
) -> None:
    token = base.client_token if role == "client" else base.manager_token

    resp = await _call(client, method, path, headers=_auth(token), body=body)

    assert resp.status_code == 403


async def test_staff_categories_access(client: AsyncClient, base: SimpleNamespace) -> None:
    anon = await client.get(STAFF_CATEGORIES)
    assert anon.status_code == 401

    client_resp = await client.get(STAFF_CATEGORIES, headers=_auth(base.client_token))
    assert client_resp.status_code == 403

    manager_resp = await client.get(STAFF_CATEGORIES, headers=_auth(base.manager_token))
    assert manager_resp.status_code == 200

    admin_resp = await client.get(STAFF_CATEGORIES, headers=_auth(base.admin_token))
    assert admin_resp.status_code == 200


# --- buildings: list and create ---


async def test_buildings_list_includes_inactive_ordered_by_address(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    inactive = await BuildingRepository(db).create("ул. В, 1")
    inactive.is_active = False
    await db.commit()

    resp = await client.get(ADMIN_BUILDINGS, headers=_auth(base.admin_token))

    assert resp.status_code == 200
    body = resp.json()
    assert [building["address"] for building in body] == ["ул. А, 1", "ул. Б, 1", "ул. В, 1"]
    assert set(body[0]) == {"id", "address", "is_active"}
    assert body[2]["is_active"] is False


async def test_create_building_returns_201_and_appears_for_staff(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    resp = await client.post(
        ADMIN_BUILDINGS, json={"address": "ул. Новая, 1"}, headers=_auth(base.admin_token)
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["address"] == "ул. Новая, 1"
    assert body["is_active"] is True
    assert set(body) == {"id", "address", "is_active"}

    staff = await client.get(STAFF_BUILDINGS, headers=_auth(base.manager_token))
    assert staff.status_code == 200
    assert any(building["id"] == body["id"] for building in staff.json())


async def test_create_building_normalizes_whitespace(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    resp = await client.post(
        ADMIN_BUILDINGS,
        json={"address": "  ул.   Мира,\n 1 "},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 201
    assert resp.json()["address"] == "ул. Мира, 1"


@pytest.mark.parametrize("length", [64, 65])
async def test_create_building_length_bounds(
    client: AsyncClient, base: SimpleNamespace, length: int
) -> None:
    resp = await client.post(
        ADMIN_BUILDINGS, json={"address": "a" * length}, headers=_auth(base.admin_token)
    )

    assert resp.status_code == (201 if length == 64 else 422)


@pytest.mark.parametrize(
    "body",
    [
        pytest.param({"address": ""}, id="empty"),
        pytest.param({"address": "   "}, id="spaces"),
        pytest.param({"address": "ул. \x00 Мира"}, id="nul"),
        pytest.param({"address": "ул. *Мира*"}, id="markup"),
        pytest.param({}, id="missing"),
        pytest.param({"address": 123}, id="number"),
    ],
)
async def test_create_building_invalid_body_is_422(
    client: AsyncClient, base: SimpleNamespace, body: dict
) -> None:
    resp = await client.post(ADMIN_BUILDINGS, json=body, headers=_auth(base.admin_token))

    assert resp.status_code == 422


async def test_create_building_duplicate_is_conflict(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    exact = await client.post(
        ADMIN_BUILDINGS, json={"address": base.building_a.address}, headers=_auth(base.admin_token)
    )
    assert exact.status_code == 409
    assert exact.json()["detail"] == BUILDING_EXISTS

    normalized = await client.post(
        ADMIN_BUILDINGS,
        json={"address": "  ул.   А,\n 1 "},
        headers=_auth(base.admin_token),
    )
    assert normalized.status_code == 409
    assert normalized.json()["detail"] == BUILDING_EXISTS


async def test_create_building_ignores_external_id(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    resp = await client.post(
        ADMIN_BUILDINGS,
        json={"address": "ул. Новая, 1", "external_id": "uk-42"},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 201
    stored = next(
        building
        for building in await BuildingRepository(db).list_all()
        if building.id == resp.json()["id"]
    )
    assert stored.external_id is None


async def test_building_limit_blocks_create_and_disabling_frees_a_slot(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    await _fill_buildings(db, DIRECTORY_ACTIVE_LIMIT - 2)

    blocked = await client.post(
        ADMIN_BUILDINGS, json={"address": "ул. Новая, 1"}, headers=_auth(base.admin_token)
    )
    assert blocked.status_code == 409
    assert blocked.json()["detail"] == BUILDINGS_LIMIT

    freed = await client.patch(
        f"{ADMIN_BUILDINGS}/{base.building_a.id}",
        json={"is_active": False},
        headers=_auth(base.admin_token),
    )
    assert freed.status_code == 200

    created = await client.post(
        ADMIN_BUILDINGS, json={"address": "ул. Новая, 1"}, headers=_auth(base.admin_token)
    )
    assert created.status_code == 201


async def test_disabled_buildings_do_not_count_toward_limit(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    await _fill_buildings(db, DIRECTORY_ACTIVE_LIMIT - 3)
    await _fill_buildings(db, 5, active=False)

    resp = await client.post(
        ADMIN_BUILDINGS, json={"address": "ул. Новая, 1"}, headers=_auth(base.admin_token)
    )

    assert resp.status_code == 201


# --- buildings: update ---


async def test_patch_building_rename_is_reflected_in_ticket(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    ticket_id = await _create_ticket(db, base, base.building_a)

    resp = await client.patch(
        f"{ADMIN_BUILDINGS}/{base.building_a.id}",
        json={"address": "ул. Ленина, 12"},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 200
    assert resp.json()["address"] == "ул. Ленина, 12"

    card = await client.get(f"/api/v1/staff/tickets/{ticket_id}", headers=_auth(base.manager_token))
    assert card.status_code == 200
    assert card.json()["building"]["address"] == "ул. Ленина, 12"


async def test_patch_building_rename_to_existing_is_conflict(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    resp = await client.patch(
        f"{ADMIN_BUILDINGS}/{base.building_a.id}",
        json={"address": base.building_b.address},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 409
    assert resp.json()["detail"] == BUILDING_EXISTS


async def test_patch_building_disable_hides_it_from_staff(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    resp = await client.patch(
        f"{ADMIN_BUILDINGS}/{base.building_a.id}",
        json={"is_active": False},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    staff = await client.get(STAFF_BUILDINGS, headers=_auth(base.manager_token))
    assert base.building_a.id not in [building["id"] for building in staff.json()]

    admin_list = await client.get(ADMIN_BUILDINGS, headers=_auth(base.admin_token))
    stored = next(b for b in admin_list.json() if b["id"] == base.building_a.id)
    assert stored["is_active"] is False


async def test_patch_building_enable_disabled_at_limit_is_conflict(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    await _fill_buildings(db, DIRECTORY_ACTIVE_LIMIT - 2)
    disabled = await BuildingRepository(db).create("ул. Отключённая, 1")
    disabled.is_active = False
    await db.commit()

    resp = await client.patch(
        f"{ADMIN_BUILDINGS}/{disabled.id}",
        json={"is_active": True},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 409
    assert resp.json()["detail"] == BUILDINGS_LIMIT

    admin_list = await client.get(ADMIN_BUILDINGS, headers=_auth(base.admin_token))
    stored = next(b for b in admin_list.json() if b["id"] == disabled.id)
    assert stored["is_active"] is False


async def test_patch_building_enable_already_enabled_at_limit_is_allowed(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    await _fill_buildings(db, DIRECTORY_ACTIVE_LIMIT - 2)

    resp = await client.patch(
        f"{ADMIN_BUILDINGS}/{base.building_a.id}",
        json={"is_active": True},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 200
    assert resp.json()["is_active"] is True


async def test_patch_building_disable_last_active_is_conflict(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    disabled = await client.patch(
        f"{ADMIN_BUILDINGS}/{base.building_b.id}",
        json={"is_active": False},
        headers=_auth(base.admin_token),
    )
    assert disabled.status_code == 200

    resp = await client.patch(
        f"{ADMIN_BUILDINGS}/{base.building_a.id}",
        json={"is_active": False},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 409
    assert resp.json()["detail"] == BUILDING_LAST_ACTIVE

    admin_list = await client.get(ADMIN_BUILDINGS, headers=_auth(base.admin_token))
    stored = next(b for b in admin_list.json() if b["id"] == base.building_a.id)
    assert stored["is_active"] is True


@pytest.mark.parametrize("body", [pytest.param({}, id="empty"), {"address": None}])
async def test_patch_building_empty_body_is_noop(
    client: AsyncClient, base: SimpleNamespace, body: dict
) -> None:
    resp = await client.patch(
        f"{ADMIN_BUILDINGS}/{base.building_a.id}", json=body, headers=_auth(base.admin_token)
    )

    assert resp.status_code == 200
    assert resp.json()["address"] == base.building_a.address
    assert resp.json()["is_active"] is True


async def test_patch_building_unknown_is_404(client: AsyncClient, base: SimpleNamespace) -> None:
    resp = await client.patch(
        f"{ADMIN_BUILDINGS}/999999",
        json={"address": "ул. Мира, 1"},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 404


@pytest.mark.parametrize("building_id", [0, -1, "abc", 2**63])
async def test_patch_building_path_bounds_are_422(
    client: AsyncClient, base: SimpleNamespace, building_id
) -> None:
    resp = await client.patch(
        f"{ADMIN_BUILDINGS}/{building_id}",
        json={"address": "ул. Мира, 1"},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 422


# --- categories: list and create ---


async def test_categories_list_includes_inactive_in_sort_order(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    inactive = await CategoryRepository(db).create("Отключённая", 5)
    inactive.is_active = False
    await db.commit()

    resp = await client.get(ADMIN_CATEGORIES, headers=_auth(base.admin_token))

    assert resp.status_code == 200
    body = resp.json()
    assert [category["title"] for category in body] == [
        "Сантехника",
        "Электрика",
        "Отключённая",
    ]
    assert set(body[0]) == {"id", "title", "is_active"}
    assert body[2]["is_active"] is False


async def test_create_category_returns_201_and_goes_last(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    resp = await client.post(
        ADMIN_CATEGORIES, json={"title": "Новая"}, headers=_auth(base.admin_token)
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Новая"
    assert body["is_active"] is True
    assert set(body) == {"id", "title", "is_active"}

    admin_list = await client.get(ADMIN_CATEGORIES, headers=_auth(base.admin_token))
    assert admin_list.json()[-1]["id"] == body["id"]

    staff = await client.get(STAFF_CATEGORIES, headers=_auth(base.manager_token))
    assert staff.json()[-1]["id"] == body["id"]


async def test_create_category_normalizes_whitespace(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    resp = await client.post(
        ADMIN_CATEGORIES,
        json={"title": "  🔥   Отопление\n "},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 201
    assert resp.json()["title"] == "🔥 Отопление"


async def test_create_category_ignores_sort_order(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    resp = await client.post(
        ADMIN_CATEGORIES,
        json={"title": "Новая", "sort_order": 99},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 201

    admin_list = await client.get(ADMIN_CATEGORIES, headers=_auth(base.admin_token))
    assert admin_list.json()[-1]["id"] == resp.json()["id"]


@pytest.mark.parametrize("length", [64, 65])
async def test_create_category_length_bounds(
    client: AsyncClient, base: SimpleNamespace, length: int
) -> None:
    resp = await client.post(
        ADMIN_CATEGORIES, json={"title": "a" * length}, headers=_auth(base.admin_token)
    )

    assert resp.status_code == (201 if length == 64 else 422)


@pytest.mark.parametrize(
    "body",
    [
        pytest.param({"title": ""}, id="empty"),
        pytest.param({"title": "   "}, id="spaces"),
        pytest.param({"title": "Сантех\x00ника"}, id="nul"),
        pytest.param({"title": "Сантех*ника"}, id="markup"),
        pytest.param({}, id="missing"),
        pytest.param({"title": 123}, id="number"),
    ],
)
async def test_create_category_invalid_body_is_422(
    client: AsyncClient, base: SimpleNamespace, body: dict
) -> None:
    resp = await client.post(ADMIN_CATEGORIES, json=body, headers=_auth(base.admin_token))

    assert resp.status_code == 422


async def test_create_category_duplicate_is_conflict(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    exact = await client.post(
        ADMIN_CATEGORIES, json={"title": base.category_a.title}, headers=_auth(base.admin_token)
    )
    assert exact.status_code == 409
    assert exact.json()["detail"] == CATEGORY_EXISTS

    normalized = await client.post(
        ADMIN_CATEGORIES, json={"title": "  Сантехника  "}, headers=_auth(base.admin_token)
    )
    assert normalized.status_code == 409
    assert normalized.json()["detail"] == CATEGORY_EXISTS


async def test_category_limit_blocks_create_and_disabling_frees_a_slot(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    await _fill_categories(db, DIRECTORY_ACTIVE_LIMIT - 2)

    blocked = await client.post(
        ADMIN_CATEGORIES, json={"title": "Новая"}, headers=_auth(base.admin_token)
    )
    assert blocked.status_code == 409
    assert blocked.json()["detail"] == CATEGORIES_LIMIT

    freed = await client.patch(
        f"{ADMIN_CATEGORIES}/{base.category_a.id}",
        json={"is_active": False},
        headers=_auth(base.admin_token),
    )
    assert freed.status_code == 200

    created = await client.post(
        ADMIN_CATEGORIES, json={"title": "Новая"}, headers=_auth(base.admin_token)
    )
    assert created.status_code == 201


async def test_disabled_categories_do_not_count_toward_limit(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    await _fill_categories(db, DIRECTORY_ACTIVE_LIMIT - 3)
    await _fill_categories(db, 5, active=False)

    resp = await client.post(
        ADMIN_CATEGORIES, json={"title": "Новая"}, headers=_auth(base.admin_token)
    )

    assert resp.status_code == 201


# --- categories: update ---


async def test_patch_category_rename_shows_for_staff(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    resp = await client.patch(
        f"{ADMIN_CATEGORIES}/{base.category_a.id}",
        json={"title": "🚰 Сантехника"},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 200
    assert resp.json()["title"] == "🚰 Сантехника"

    staff = await client.get(STAFF_CATEGORIES, headers=_auth(base.manager_token))
    stored = next(category for category in staff.json() if category["id"] == base.category_a.id)
    assert stored["title"] == "🚰 Сантехника"


async def test_patch_category_rename_to_existing_is_conflict(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    resp = await client.patch(
        f"{ADMIN_CATEGORIES}/{base.category_a.id}",
        json={"title": base.category_b.title},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 409
    assert resp.json()["detail"] == CATEGORY_EXISTS


async def test_patch_category_disable_hides_it_from_staff(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    resp = await client.patch(
        f"{ADMIN_CATEGORIES}/{base.category_a.id}",
        json={"is_active": False},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    staff = await client.get(STAFF_CATEGORIES, headers=_auth(base.manager_token))
    assert base.category_a.id not in [category["id"] for category in staff.json()]

    admin_list = await client.get(ADMIN_CATEGORIES, headers=_auth(base.admin_token))
    stored = next(c for c in admin_list.json() if c["id"] == base.category_a.id)
    assert stored["is_active"] is False


async def test_patch_category_enable_disabled_at_limit_is_conflict(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    await _fill_categories(db, DIRECTORY_ACTIVE_LIMIT - 2)
    disabled = await CategoryRepository(db).create("Отключённая", 100)
    disabled.is_active = False
    await db.commit()

    resp = await client.patch(
        f"{ADMIN_CATEGORIES}/{disabled.id}",
        json={"is_active": True},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 409
    assert resp.json()["detail"] == CATEGORIES_LIMIT

    admin_list = await client.get(ADMIN_CATEGORIES, headers=_auth(base.admin_token))
    stored = next(c for c in admin_list.json() if c["id"] == disabled.id)
    assert stored["is_active"] is False


async def test_patch_category_enable_already_enabled_at_limit_is_allowed(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    await _fill_categories(db, DIRECTORY_ACTIVE_LIMIT - 2)

    resp = await client.patch(
        f"{ADMIN_CATEGORIES}/{base.category_a.id}",
        json={"is_active": True},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 200
    assert resp.json()["is_active"] is True


async def test_patch_category_disable_last_active_is_conflict(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    disabled = await client.patch(
        f"{ADMIN_CATEGORIES}/{base.category_b.id}",
        json={"is_active": False},
        headers=_auth(base.admin_token),
    )
    assert disabled.status_code == 200

    resp = await client.patch(
        f"{ADMIN_CATEGORIES}/{base.category_a.id}",
        json={"is_active": False},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 409
    assert resp.json()["detail"] == CATEGORY_LAST_ACTIVE

    admin_list = await client.get(ADMIN_CATEGORIES, headers=_auth(base.admin_token))
    stored = next(c for c in admin_list.json() if c["id"] == base.category_a.id)
    assert stored["is_active"] is True


@pytest.mark.parametrize("body", [pytest.param({}, id="empty"), {"title": None}])
async def test_patch_category_empty_body_is_noop(
    client: AsyncClient, base: SimpleNamespace, body: dict
) -> None:
    resp = await client.patch(
        f"{ADMIN_CATEGORIES}/{base.category_a.id}", json=body, headers=_auth(base.admin_token)
    )

    assert resp.status_code == 200
    assert resp.json()["title"] == base.category_a.title
    assert resp.json()["is_active"] is True


async def test_patch_category_unknown_is_404(client: AsyncClient, base: SimpleNamespace) -> None:
    resp = await client.patch(
        f"{ADMIN_CATEGORIES}/999999", json={"title": "Новая"}, headers=_auth(base.admin_token)
    )

    assert resp.status_code == 404


@pytest.mark.parametrize("category_id", [0, -1, "abc", 2**63])
async def test_patch_category_path_bounds_are_422(
    client: AsyncClient, base: SimpleNamespace, category_id
) -> None:
    resp = await client.patch(
        f"{ADMIN_CATEGORIES}/{category_id}",
        json={"title": "Новая"},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 422


# --- categories: order ---


async def test_order_reverses_and_both_lists_follow(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    created = await client.post(
        ADMIN_CATEGORIES, json={"title": "Третья"}, headers=_auth(base.admin_token)
    )
    third_id = created.json()["id"]
    ids = [third_id, base.category_b.id, base.category_a.id]

    resp = await client.put(ADMIN_ORDER, json={"ids": ids}, headers=_auth(base.admin_token))

    assert resp.status_code == 200
    assert [category["id"] for category in resp.json()] == ids

    admin_list = await client.get(ADMIN_CATEGORIES, headers=_auth(base.admin_token))
    assert [category["id"] for category in admin_list.json()] == ids

    staff = await client.get(STAFF_CATEGORIES, headers=_auth(base.manager_token))
    assert [category["id"] for category in staff.json()] == ids


async def test_order_includes_disabled_for_admin_and_hides_for_staff(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    disabled = await CategoryRepository(db).create("Отключённая", 3)
    disabled.is_active = False
    await db.commit()
    ids = [disabled.id, base.category_b.id, base.category_a.id]

    resp = await client.put(ADMIN_ORDER, json={"ids": ids}, headers=_auth(base.admin_token))

    assert resp.status_code == 200
    admin_list = await client.get(ADMIN_CATEGORIES, headers=_auth(base.admin_token))
    assert [category["id"] for category in admin_list.json()] == ids

    staff = await client.get(STAFF_CATEGORIES, headers=_auth(base.manager_token))
    assert [category["id"] for category in staff.json()] == [base.category_b.id, base.category_a.id]


async def test_order_missing_category_is_conflict_and_unchanged(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    disabled = await CategoryRepository(db).create("Отключённая", 3)
    disabled.is_active = False
    await db.commit()
    before = (await client.get(ADMIN_CATEGORIES, headers=_auth(base.admin_token))).json()

    resp = await client.put(
        ADMIN_ORDER,
        json={"ids": [base.category_b.id, base.category_a.id]},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 409
    assert resp.json()["detail"] == CATEGORY_ORDER_STALE
    after = (await client.get(ADMIN_CATEGORIES, headers=_auth(base.admin_token))).json()
    assert after == before


async def test_order_unknown_id_is_conflict_and_unchanged(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    disabled = await CategoryRepository(db).create("Отключённая", 3)
    disabled.is_active = False
    await db.commit()
    before = (await client.get(ADMIN_CATEGORIES, headers=_auth(base.admin_token))).json()

    resp = await client.put(
        ADMIN_ORDER,
        json={"ids": [base.category_a.id, base.category_b.id, 999999]},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 409
    assert resp.json()["detail"] == CATEGORY_ORDER_STALE
    after = (await client.get(ADMIN_CATEGORIES, headers=_auth(base.admin_token))).json()
    assert after == before


async def test_order_duplicate_is_conflict_and_unchanged(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    before = (await client.get(ADMIN_CATEGORIES, headers=_auth(base.admin_token))).json()

    all_ids = [category["id"] for category in before]
    for ids in ([base.category_a.id, base.category_a.id], [*all_ids, all_ids[0]]):
        resp = await client.put(ADMIN_ORDER, json={"ids": ids}, headers=_auth(base.admin_token))

        assert resp.status_code == 409
        assert resp.json()["detail"] == CATEGORY_ORDER_STALE
    after = (await client.get(ADMIN_CATEGORIES, headers=_auth(base.admin_token))).json()
    assert after == before


@pytest.mark.parametrize(
    "ids",
    [
        pytest.param([], id="empty"),
        pytest.param([0], id="zero"),
        pytest.param([2**63], id="too-big"),
        pytest.param(["x"], id="not-int"),
    ],
)
async def test_order_invalid_ids_are_422(
    client: AsyncClient, base: SimpleNamespace, ids: list
) -> None:
    resp = await client.put(ADMIN_ORDER, json={"ids": ids}, headers=_auth(base.admin_token))

    assert resp.status_code == 422


async def test_staff_categories_only_active_with_short_keys(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    disabled = await CategoryRepository(db).create("Отключённая", 3)
    disabled.is_active = False
    await db.commit()

    resp = await client.get(STAFF_CATEGORIES, headers=_auth(base.manager_token))

    assert resp.status_code == 200
    body = resp.json()
    assert [category["id"] for category in body] == [base.category_a.id, base.category_b.id]
    assert set(body[0]) == {"id", "title"}
