from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import SenderType, TicketStatus, TicketType, UserRole
from src.core.security import hash_token
from src.main import app
from src.models.message import Message
from src.providers.factory import get_storage_provider
from src.providers.local_storage_provider import LocalStorageProvider
from src.repositories.auth_token_repository import AuthTokenRepository
from src.repositories.building_repository import BuildingRepository
from src.repositories.category_repository import CategoryRepository
from src.repositories.status_change_repository import StatusChangeRepository
from src.repositories.ticket_repository import TicketRepository
from src.repositories.user_repository import UserRepository
from src.services.file_service import FileService

NOW = datetime(2026, 9, 25, 12, 0, tzinfo=UTC)


@pytest.fixture
def storage(tmp_path) -> LocalStorageProvider:
    provider = LocalStorageProvider(str(tmp_path))
    app.dependency_overrides[get_storage_provider] = lambda: provider
    return provider


async def _issue_token(db: AsyncSession, user) -> str:
    token = f"staff-token-{user.id}"
    await AuthTokenRepository(db).create(
        user.id, hash_token(token), datetime.now(UTC) + timedelta(days=1)
    )
    return token


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def base(db: AsyncSession) -> SimpleNamespace:
    users = UserRepository(db)
    client = await users.create(max_user_id=1000003, first_name="Мария", phone="+7 (900) 111-11-11")
    manager = await users.create(max_user_id=1000002, first_name="Игорь", role=UserRole.MANAGER)
    admin = await users.create(max_user_id=1000001, first_name="Анна", role=UserRole.ADMIN)
    other_manager = await users.create(
        max_user_id=1000004, first_name="Пётр", role=UserRole.MANAGER
    )

    buildings = BuildingRepository(db)
    building_a = await buildings.create("ул. Ленина, 12")
    building_b = await buildings.create("ул. Гагарина, 5")

    categories = CategoryRepository(db)
    category_a = await categories.create("Сантехника", 1)
    category_b = await categories.create("Электрика", 2)

    manager_token = await _issue_token(db, manager)
    admin_token = await _issue_token(db, admin)
    client_token = await _issue_token(db, client)
    await db.commit()

    return SimpleNamespace(
        client=client,
        manager=manager,
        admin=admin,
        other_manager=other_manager,
        building_a=building_a,
        building_b=building_b,
        category_a=category_a,
        category_b=category_b,
        manager_token=manager_token,
        admin_token=admin_token,
        client_token=client_token,
    )


async def _create_ticket(
    db: AsyncSession,
    base: SimpleNamespace,
    *,
    status: TicketStatus,
    created_at: datetime,
    type: TicketType = TicketType.REQUEST,
    building=None,
    category=None,
    assignee=None,
    client=None,
    description: str = "Описание обращения",
) -> int:
    if type == TicketType.REQUEST:
        building = building or base.building_a
        category = category or base.category_a
    ticket = await TicketRepository(db).create(
        type=type,
        status=status,
        client_id=(client or base.client).id,
        description=description,
        category_id=category.id if category else None,
        building_id=building.id if building else None,
        apartment="45" if building else None,
        contact_phone="+7 (900) 111-11-11",
        assignee_id=assignee.id if assignee else None,
        created_at=created_at,
    )
    await db.commit()
    return ticket.id


async def test_list_returns_only_open_tickets_newest_first(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    new_id = await _create_ticket(
        db, base, status=TicketStatus.NEW, created_at=NOW - timedelta(hours=1)
    )
    in_progress_id = await _create_ticket(
        db, base, status=TicketStatus.IN_PROGRESS, created_at=NOW - timedelta(hours=2)
    )
    waiting_id = await _create_ticket(
        db, base, status=TicketStatus.WAITING_CLIENT, created_at=NOW - timedelta(hours=3)
    )
    closed_id = await _create_ticket(
        db, base, status=TicketStatus.CLOSED, created_at=NOW - timedelta(hours=4)
    )
    rejected_id = await _create_ticket(
        db, base, status=TicketStatus.REJECTED, created_at=NOW - timedelta(hours=5)
    )

    resp = await client.get("/api/v1/staff/tickets", headers=_auth(base.manager_token))

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert [item["id"] for item in body["items"]] == [new_id, in_progress_id, waiting_id]
    assert {item["status"] for item in body["items"]} == {
        TicketStatus.NEW,
        TicketStatus.IN_PROGRESS,
        TicketStatus.WAITING_CLIENT,
    }
    assert closed_id not in [item["id"] for item in body["items"]]
    assert rejected_id not in [item["id"] for item in body["items"]]


async def test_list_filter_by_status(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    await _create_ticket(db, base, status=TicketStatus.NEW, created_at=NOW - timedelta(hours=1))
    in_progress_id = await _create_ticket(
        db, base, status=TicketStatus.IN_PROGRESS, created_at=NOW - timedelta(hours=2)
    )

    resp = await client.get(
        "/api/v1/staff/tickets",
        params={"status": "IN_PROGRESS"},
        headers=_auth(base.manager_token),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert [item["id"] for item in body["items"]] == [in_progress_id]


async def test_list_filter_by_building(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    in_building = await _create_ticket(
        db,
        base,
        status=TicketStatus.NEW,
        created_at=NOW - timedelta(hours=1),
        building=base.building_a,
    )
    await _create_ticket(
        db,
        base,
        status=TicketStatus.NEW,
        created_at=NOW - timedelta(hours=2),
        building=base.building_b,
    )

    resp = await client.get(
        "/api/v1/staff/tickets",
        params={"building_id": base.building_a.id},
        headers=_auth(base.manager_token),
    )

    body = resp.json()
    assert body["total"] == 1
    assert [item["id"] for item in body["items"]] == [in_building]


async def test_list_filter_by_category(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    matching = await _create_ticket(
        db,
        base,
        status=TicketStatus.NEW,
        created_at=NOW - timedelta(hours=1),
        category=base.category_a,
    )
    await _create_ticket(
        db,
        base,
        status=TicketStatus.NEW,
        created_at=NOW - timedelta(hours=2),
        category=base.category_b,
    )

    resp = await client.get(
        "/api/v1/staff/tickets",
        params={"category_id": base.category_a.id},
        headers=_auth(base.manager_token),
    )

    body = resp.json()
    assert body["total"] == 1
    assert [item["id"] for item in body["items"]] == [matching]


async def test_list_filter_mine(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    mine = await _create_ticket(
        db,
        base,
        status=TicketStatus.NEW,
        created_at=NOW - timedelta(hours=1),
        assignee=base.manager,
    )
    await _create_ticket(
        db,
        base,
        status=TicketStatus.NEW,
        created_at=NOW - timedelta(hours=2),
        assignee=base.other_manager,
    )
    await _create_ticket(db, base, status=TicketStatus.NEW, created_at=NOW - timedelta(hours=3))

    resp = await client.get(
        "/api/v1/staff/tickets",
        params={"mine": "true"},
        headers=_auth(base.manager_token),
    )

    body = resp.json()
    assert body["total"] == 1
    assert [item["id"] for item in body["items"]] == [mine]
    assert body["items"][0]["assignee"]["id"] == base.manager.id


async def test_list_filter_combination(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    matching = await _create_ticket(
        db,
        base,
        status=TicketStatus.IN_PROGRESS,
        created_at=NOW - timedelta(hours=1),
        building=base.building_a,
        category=base.category_a,
        assignee=base.manager,
    )
    await _create_ticket(
        db,
        base,
        status=TicketStatus.IN_PROGRESS,
        created_at=NOW - timedelta(hours=2),
        building=base.building_b,
        category=base.category_a,
        assignee=base.manager,
    )
    await _create_ticket(
        db,
        base,
        status=TicketStatus.NEW,
        created_at=NOW - timedelta(hours=3),
        building=base.building_a,
        category=base.category_a,
        assignee=base.manager,
    )

    resp = await client.get(
        "/api/v1/staff/tickets",
        params={
            "status": "IN_PROGRESS",
            "building_id": base.building_a.id,
            "category_id": base.category_a.id,
            "mine": "true",
        },
        headers=_auth(base.manager_token),
    )

    body = resp.json()
    assert body["total"] == 1
    assert [item["id"] for item in body["items"]] == [matching]


async def test_list_pagination(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    newest = await _create_ticket(
        db, base, status=TicketStatus.NEW, created_at=NOW - timedelta(hours=1)
    )
    middle = await _create_ticket(
        db, base, status=TicketStatus.NEW, created_at=NOW - timedelta(hours=2)
    )
    oldest = await _create_ticket(
        db, base, status=TicketStatus.NEW, created_at=NOW - timedelta(hours=3)
    )

    resp = await client.get(
        "/api/v1/staff/tickets",
        params={"skip": 1, "limit": 1},
        headers=_auth(base.manager_token),
    )

    body = resp.json()
    assert body["total"] == 3
    assert [item["id"] for item in body["items"]] == [middle]

    first_page = await client.get(
        "/api/v1/staff/tickets",
        params={"skip": 0, "limit": 2},
        headers=_auth(base.manager_token),
    )
    assert [item["id"] for item in first_page.json()["items"]] == [newest, middle]
    assert first_page.json()["total"] == 3
    assert oldest not in [item["id"] for item in first_page.json()["items"]]


async def test_list_allowed_for_manager_and_admin(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    await _create_ticket(db, base, status=TicketStatus.NEW, created_at=NOW)

    manager_resp = await client.get("/api/v1/staff/tickets", headers=_auth(base.manager_token))
    admin_resp = await client.get("/api/v1/staff/tickets", headers=_auth(base.admin_token))

    assert manager_resp.status_code == 200
    assert admin_resp.status_code == 200


async def test_list_requires_token(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/staff/tickets")

    assert resp.status_code == 401


async def test_list_forbidden_for_client(client: AsyncClient, base: SimpleNamespace) -> None:
    resp = await client.get("/api/v1/staff/tickets", headers=_auth(base.client_token))

    assert resp.status_code == 403


async def test_list_rejects_closed_status(client: AsyncClient, base: SimpleNamespace) -> None:
    resp = await client.get(
        "/api/v1/staff/tickets",
        params={"status": "CLOSED"},
        headers=_auth(base.manager_token),
    )

    assert resp.status_code == 422


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"skip": -1}])
async def test_list_rejects_invalid_pagination(
    client: AsyncClient, base: SimpleNamespace, params: dict
) -> None:
    resp = await client.get(
        "/api/v1/staff/tickets", params=params, headers=_auth(base.manager_token)
    )

    assert resp.status_code == 422


@pytest.mark.parametrize(
    "params",
    [
        {"building_id": 2**63},
        {"category_id": 2**63},
        {"skip": 2**63},
    ],
)
async def test_list_rejects_out_of_range_bigint(
    client: AsyncClient, base: SimpleNamespace, params: dict
) -> None:
    resp = await client.get(
        "/api/v1/staff/tickets", params=params, headers=_auth(base.manager_token)
    )

    assert resp.status_code == 422


async def test_list_accepts_max_bigint_filters(client: AsyncClient, base: SimpleNamespace) -> None:
    for params in (
        {"building_id": 2**63 - 1},
        {"category_id": 2**63 - 1},
        {"skip": 2**63 - 1},
    ):
        resp = await client.get(
            "/api/v1/staff/tickets", params=params, headers=_auth(base.manager_token)
        )
        assert resp.status_code == 200
        assert resp.json()["items"] == []


async def test_card_rejects_out_of_range_ticket_id(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    resp = await client.get(f"/api/v1/staff/tickets/{2**63}", headers=_auth(base.manager_token))

    assert resp.status_code == 422


async def test_card_accepts_max_bigint_ticket_id(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    resp = await client.get(f"/api/v1/staff/tickets/{2**63 - 1}", headers=_auth(base.manager_token))

    assert resp.status_code == 404


async def test_list_no_matches_returns_empty(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    await _create_ticket(
        db,
        base,
        status=TicketStatus.NEW,
        created_at=NOW,
        building=base.building_a,
        category=base.category_a,
    )

    resp = await client.get(
        "/api/v1/staff/tickets",
        params={"category_id": 999999},
        headers=_auth(base.manager_token),
    )

    assert resp.status_code == 200
    assert resp.json() == {"total": 0, "items": []}


async def test_ticket_detail_nested_files_and_history(
    client: AsyncClient,
    db: AsyncSession,
    base: SimpleNamespace,
    storage: LocalStorageProvider,
) -> None:
    ticket_id = await _create_ticket(
        db,
        base,
        status=TicketStatus.IN_PROGRESS,
        created_at=NOW - timedelta(hours=1),
        building=base.building_a,
        category=base.category_a,
        assignee=base.manager,
    )

    photo = await FileService(db, storage).save(
        b"photo-bytes", "image/png", original_name="photo.png", ticket_id=ticket_id
    )
    message = Message(
        ticket_id=ticket_id,
        sender_type=SenderType.STAFF,
        author_id=base.manager.id,
        text="Смотрим",
    )
    db.add(message)
    await db.flush()
    await FileService(db, storage).save(
        b"chat-bytes", "image/jpeg", ticket_id=ticket_id, message_id=message.id
    )

    changes = StatusChangeRepository(db)
    await changes.create(
        ticket_id,
        None,
        TicketStatus.NEW,
        changed_by_id=base.client.id,
        created_at=NOW - timedelta(hours=2),
    )
    await changes.create(
        ticket_id,
        TicketStatus.NEW,
        TicketStatus.IN_PROGRESS,
        changed_by_id=base.manager.id,
        created_at=NOW - timedelta(hours=1),
    )
    await db.commit()

    resp = await client.get(f"/api/v1/staff/tickets/{ticket_id}", headers=_auth(base.manager_token))

    assert resp.status_code == 200
    body = resp.json()
    assert body["client"]["id"] == base.client.id
    assert body["client"]["phone"] == "+7 (900) 111-11-11"
    assert body["assignee"]["id"] == base.manager.id
    assert body["category"]["title"] == "Сантехника"
    assert body["building"]["address"] == "ул. Ленина, 12"
    assert body["apartment"] == "45"

    assert len(body["files"]) == 1
    assert body["files"][0]["id"] == photo.id
    assert body["files"][0]["original_name"] == "photo.png"
    assert body["files"][0]["url"]

    download = await client.get(body["files"][0]["url"])
    assert download.status_code == 200
    assert download.content == b"photo-bytes"

    assert [change["to_status"] for change in body["history"]] == [
        "NEW",
        "IN_PROGRESS",
    ]
    assert body["history"][0]["from_status"] is None
    assert body["history"][0]["changed_by"]["id"] == base.client.id
    assert body["history"][1]["changed_by"]["id"] == base.manager.id


async def test_closed_ticket_card_works(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    ticket_id = await _create_ticket(
        db,
        base,
        status=TicketStatus.CLOSED,
        created_at=NOW - timedelta(days=3),
        building=base.building_a,
        category=base.category_a,
    )

    resp = await client.get(f"/api/v1/staff/tickets/{ticket_id}", headers=_auth(base.manager_token))

    assert resp.status_code == 200
    assert resp.json()["status"] == "CLOSED"


async def test_unknown_ticket_returns_404(client: AsyncClient, base: SimpleNamespace) -> None:
    resp = await client.get("/api/v1/staff/tickets/999999", headers=_auth(base.manager_token))

    assert resp.status_code == 404
    assert resp.json() == {"detail": "Обращение не найдено"}


async def test_ticket_detail_requires_token(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/staff/tickets/1")

    assert resp.status_code == 401


async def test_ticket_detail_forbidden_for_client(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    resp = await client.get("/api/v1/staff/tickets/1", headers=_auth(base.client_token))

    assert resp.status_code == 403
