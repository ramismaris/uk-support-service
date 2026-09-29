from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import TicketStatus, TicketType, UserRole
from src.core.security import hash_token
from src.repositories.auth_token_repository import AuthTokenRepository
from src.repositories.building_repository import BuildingRepository
from src.repositories.category_repository import CategoryRepository
from src.repositories.status_change_repository import StatusChangeRepository
from src.repositories.ticket_repository import TicketRepository
from src.repositories.user_repository import UserRepository

PATH = "/api/v1/admin/dashboard"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _issue_token(db: AsyncSession, user, *, label: str) -> str:
    token = f"dashboard-token-{user.id}-{label}"
    await AuthTokenRepository(db).create(
        user.id, hash_token(token), datetime.now(UTC) + timedelta(days=1)
    )
    return token


@pytest.fixture
async def base(db: AsyncSession) -> SimpleNamespace:
    users = UserRepository(db)
    client = await users.create(max_user_id=2000001, first_name="Мария")
    manager = await users.create(max_user_id=2000002, first_name="Игорь", role=UserRole.MANAGER)
    admin = await users.create(max_user_id=2000003, first_name="Анна", role=UserRole.ADMIN)

    client_token = await _issue_token(db, client, label="live")
    manager_token = await _issue_token(db, manager, label="live")
    admin_token = await _issue_token(db, admin, label="live")
    await db.commit()

    return SimpleNamespace(
        client=client,
        manager=manager,
        admin=admin,
        client_token=client_token,
        manager_token=manager_token,
        admin_token=admin_token,
    )


@pytest.fixture
async def scenario(db: AsyncSession, base: SimpleNamespace) -> SimpleNamespace:
    building = await BuildingRepository(db).create("ул. Ленина, 12")
    category = await CategoryRepository(db).create("🚰 Сантехника", 1)
    now = datetime.now(UTC)

    created_old = now - timedelta(days=2)
    reacted_at = created_old + timedelta(minutes=90)
    closed_at = created_old + timedelta(days=1)
    closed_ticket = await TicketRepository(db).create(
        type=TicketType.REQUEST,
        status=TicketStatus.CLOSED,
        client_id=base.client.id,
        description="Течёт кран",
        category_id=category.id,
        building_id=building.id,
        apartment="45",
        rating=5,
        created_at=created_old,
        closed_at=closed_at,
    )
    changes = StatusChangeRepository(db)
    await changes.create(closed_ticket.id, None, TicketStatus.NEW, created_at=created_old)
    await changes.create(
        closed_ticket.id, TicketStatus.NEW, TicketStatus.IN_PROGRESS, created_at=reacted_at
    )
    await changes.create(
        closed_ticket.id, TicketStatus.IN_PROGRESS, TicketStatus.CLOSED, created_at=closed_at
    )

    overdue_ticket = await TicketRepository(db).create(
        type=TicketType.REQUEST,
        status=TicketStatus.NEW,
        client_id=base.client.id,
        description="Не работает лифт",
        category_id=category.id,
        building_id=building.id,
        apartment="45",
        created_at=now - timedelta(hours=5),
    )
    await changes.create(
        overdue_ticket.id, None, TicketStatus.NEW, created_at=now - timedelta(hours=5)
    )
    await db.commit()

    return SimpleNamespace(
        category=category, closed_ticket=closed_ticket, overdue_ticket=overdue_ticket
    )


async def test_access_control(client: AsyncClient, base: SimpleNamespace) -> None:
    anon = await client.get(PATH)
    assert anon.status_code == 401

    client_resp = await client.get(PATH, headers=_auth(base.client_token))
    assert client_resp.status_code == 403

    manager_resp = await client.get(PATH, headers=_auth(base.manager_token))
    assert manager_resp.status_code == 403

    admin_resp = await client.get(PATH, headers=_auth(base.admin_token))
    assert admin_resp.status_code == 200


@pytest.mark.parametrize("period", [7, 30, 90])
async def test_period_controls_daily_points(
    client: AsyncClient, base: SimpleNamespace, period: int
) -> None:
    resp = await client.get(PATH, params={"period": period}, headers=_auth(base.admin_token))

    assert resp.status_code == 200
    body = resp.json()
    assert body["period_days"] == period
    assert len(body["daily"]) == period
    assert body["daily"][0]["date"] < body["daily"][-1]["date"]


async def test_period_defaults_to_30(client: AsyncClient, base: SimpleNamespace) -> None:
    resp = await client.get(PATH, headers=_auth(base.admin_token))

    assert resp.status_code == 200
    assert resp.json()["period_days"] == 30
    assert len(resp.json()["daily"]) == 30


@pytest.mark.parametrize("period", [0, 1, 31, "abc", 9223372036854775808])
async def test_invalid_period_is_422(
    client: AsyncClient, base: SimpleNamespace, period: object
) -> None:
    resp = await client.get(PATH, params={"period": period}, headers=_auth(base.admin_token))

    assert resp.status_code == 422


async def test_empty_database_returns_zeros_and_nones(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    resp = await client.get(PATH, headers=_auth(base.admin_token))

    assert resp.status_code == 200
    body = resp.json()
    assert body["now"] == {"new": 0, "in_progress": 0, "waiting_client": 0, "overdue": 0}
    assert body["summary"]["created"] == {"value": 0, "previous": 0}
    assert body["summary"]["closed"] == {"value": 0, "previous": 0}
    assert body["summary"]["reaction_minutes"] == {"value": None, "previous": None}
    assert body["summary"]["resolution_hours"] == {"value": None, "previous": None}
    assert body["summary"]["rating"] == {"value": None, "previous": None, "count": 0}
    assert body["categories"] == []
    assert body["questions"] == {"created": 0, "resolution_hours": None}
    assert all(day["created"] == 0 and day["closed"] == 0 for day in body["daily"])


async def test_scenario_over_real_database(
    client: AsyncClient, base: SimpleNamespace, scenario: SimpleNamespace
) -> None:
    resp = await client.get(PATH, headers=_auth(base.admin_token))

    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"]["created"]["value"] == 2
    assert body["summary"]["closed"]["value"] == 1
    assert body["summary"]["reaction_minutes"]["value"] == 90.0
    assert body["now"]["overdue"] == 1
    assert "🚰 Сантехника" in [category["title"] for category in body["categories"]]
    assert sum(day["created"] for day in body["daily"]) == 2
    assert sum(day["closed"] for day in body["daily"]) == 1
    assert body["sla"] == {"reaction_hours": 4, "resolution_hours": 72}
