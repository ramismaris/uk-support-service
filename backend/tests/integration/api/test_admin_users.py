import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

import httpx_ws
import pytest
from httpx import AsyncClient
from httpx_ws import aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.constants import UserRole
from src.core.security import hash_token
from src.core.ws_manager import ws_manager
from src.main import app
from src.repositories.auth_token_repository import AuthTokenRepository
from src.repositories.user_repository import UserRepository

WS_PATH = "/api/v1/ws"


def _ws_http() -> AsyncClient:
    return AsyncClient(transport=ASGIWebSocketTransport(app), base_url="http://test")


async def _receive_json(ws) -> dict:
    async with asyncio.timeout(5):
        return await ws.receive_json()


async def _wait_until(predicate) -> None:
    async with asyncio.timeout(5):
        while not predicate():
            await asyncio.sleep(0.01)


async def _expect_close(ws) -> int:
    async with asyncio.timeout(5):
        while True:
            try:
                await ws.receive_json()
            except httpx_ws.WebSocketDisconnect as exc:
                return exc.code
            except BaseExceptionGroup as group:
                for error in group.exceptions:
                    if isinstance(error, httpx_ws.WebSocketDisconnect):
                        return error.code
                raise


@pytest.fixture(autouse=True)
def reset_ws_manager() -> Iterator[None]:
    ws_manager._connections.clear()
    yield
    ws_manager._connections.clear()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _issue_token(db: AsyncSession, user, *, label: str) -> str:
    token = f"admin-token-{user.id}-{label}"
    await AuthTokenRepository(db).create(
        user.id, hash_token(token), datetime.now(UTC) + timedelta(days=1)
    )
    return token


@pytest.fixture
async def base(db: AsyncSession) -> SimpleNamespace:
    users = UserRepository(db)
    client = await users.create(max_user_id=1000003, first_name="Мария", phone="+7 (900) 111-11-11")
    manager = await users.create(max_user_id=1000002, first_name="Игорь", role=UserRole.MANAGER)
    admin = await users.create(max_user_id=1000001, first_name="Анна", role=UserRole.ADMIN)
    other_manager = await users.create(
        max_user_id=1000004, first_name="Пётр", role=UserRole.MANAGER
    )
    blocked_admin = await users.create(
        max_user_id=1000005, first_name="Виктор", role=UserRole.ADMIN
    )
    blocked_admin.is_blocked = True

    manager_token = await _issue_token(db, manager, label="live")
    admin_token = await _issue_token(db, admin, label="live")
    client_token = await _issue_token(db, client, label="live")
    other_manager_token = await _issue_token(db, other_manager, label="live")
    blocked_admin_token = await _issue_token(db, blocked_admin, label="live")
    await db.commit()

    return SimpleNamespace(
        client=client,
        manager=manager,
        admin=admin,
        other_manager=other_manager,
        blocked_admin=blocked_admin,
        manager_token=manager_token,
        admin_token=admin_token,
        client_token=client_token,
        other_manager_token=other_manager_token,
        blocked_admin_token=blocked_admin_token,
    )


async def test_list_returns_users_with_new_fields(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    resp = await client.get("/api/v1/admin/users", headers=_auth(base.admin_token))

    assert resp.status_code == 200
    body = resp.json()
    ids = [item["id"] for item in body["items"]]
    assert base.client.id in ids
    assert body["total"] >= 4

    item = next(i for i in body["items"] if i["id"] == base.manager.id)
    assert item["role"] == "MANAGER"
    assert item["is_blocked"] is False
    assert item["created_at"]
    assert "last_seen_at" in item


async def test_list_filters_by_roles_and_is_blocked(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    resp = await client.get(
        "/api/v1/admin/users",
        params={"role": ["MANAGER", "ADMIN"]},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 200
    roles = {item["role"] for item in resp.json()["items"]}
    assert roles <= {"MANAGER", "ADMIN"}
    assert all(item["id"] != base.client.id for item in resp.json()["items"])

    blocked = await client.get(
        "/api/v1/admin/users",
        params={"is_blocked": "true"},
        headers=_auth(base.admin_token),
    )
    assert blocked.status_code == 200
    assert [item["id"] for item in blocked.json()["items"]] == [base.blocked_admin.id]


async def test_list_search_by_name_and_by_max_id(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    by_name = await client.get(
        "/api/v1/admin/users", params={"q": "Игор"}, headers=_auth(base.admin_token)
    )
    assert by_name.status_code == 200
    assert [item["id"] for item in by_name.json()["items"]] == [base.manager.id]

    by_max_id = await client.get(
        "/api/v1/admin/users", params={"q": "1000003"}, headers=_auth(base.admin_token)
    )
    assert by_max_id.status_code == 200
    assert [item["id"] for item in by_max_id.json()["items"]] == [base.client.id]


async def test_patch_changes_role(client: AsyncClient, base: SimpleNamespace) -> None:
    resp = await client.patch(
        f"/api/v1/admin/users/{base.manager.id}",
        json={"role": "ADMIN"},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 200
    assert resp.json()["role"] == "ADMIN"
    assert resp.json()["is_blocked"] is False

    listed = await client.get(
        "/api/v1/admin/users", params={"q": "Игор"}, headers=_auth(base.admin_token)
    )
    assert listed.json()["items"][0]["role"] == "ADMIN"


async def test_block_and_unblock_revoke_and_restore_access(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    block = await client.patch(
        f"/api/v1/admin/users/{base.manager.id}",
        json={"is_blocked": True},
        headers=_auth(base.admin_token),
    )
    assert block.status_code == 200
    assert block.json()["is_blocked"] is True

    me = await client.get("/api/v1/me", headers=_auth(base.manager_token))
    assert me.status_code == 403

    unblock = await client.patch(
        f"/api/v1/admin/users/{base.manager.id}",
        json={"is_blocked": False},
        headers=_auth(base.admin_token),
    )
    assert unblock.status_code == 200

    me_again = await client.get("/api/v1/me", headers=_auth(base.manager_token))
    assert me_again.status_code == 200


async def test_demoted_manager_loses_staff_access(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    resp = await client.patch(
        f"/api/v1/admin/users/{base.manager.id}",
        json={"role": "CLIENT"},
        headers=_auth(base.admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "CLIENT"

    staff = await client.get("/api/v1/staff/tickets", headers=_auth(base.manager_token))
    assert staff.status_code == 403


async def test_patch_self_demotion_and_block_are_conflicts(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    demote = await client.patch(
        f"/api/v1/admin/users/{base.admin.id}",
        json={"role": "MANAGER"},
        headers=_auth(base.admin_token),
    )
    assert demote.status_code == 409

    block = await client.patch(
        f"/api/v1/admin/users/{base.admin.id}",
        json={"is_blocked": True},
        headers=_auth(base.admin_token),
    )
    assert block.status_code == 409


async def test_patch_config_admin_cannot_be_demoted_or_blocked(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    config_admin = await UserRepository(db).create(
        max_user_id=777000, first_name="Конфиг", role=UserRole.ADMIN
    )
    await db.commit()

    with patch.object(settings, "admin_max_user_ids", [777000]):
        demote = await client.patch(
            f"/api/v1/admin/users/{config_admin.id}",
            json={"role": "MANAGER"},
            headers=_auth(base.admin_token),
        )
        assert demote.status_code == 409

        block = await client.patch(
            f"/api/v1/admin/users/{config_admin.id}",
            json={"is_blocked": True},
            headers=_auth(base.admin_token),
        )
        assert block.status_code == 409

        unblock = await client.patch(
            f"/api/v1/admin/users/{config_admin.id}",
            json={"is_blocked": False},
            headers=_auth(base.admin_token),
        )
        assert unblock.status_code == 200


async def test_patch_unknown_user_returns_404(client: AsyncClient, base: SimpleNamespace) -> None:
    resp = await client.patch(
        "/api/v1/admin/users/999999", json={"role": "MANAGER"}, headers=_auth(base.admin_token)
    )

    assert resp.status_code == 404


async def test_patch_empty_body_is_a_noop(client: AsyncClient, base: SimpleNamespace) -> None:
    resp = await client.patch(
        f"/api/v1/admin/users/{base.manager.id}", json={}, headers=_auth(base.admin_token)
    )

    assert resp.status_code == 200
    assert resp.json()["role"] == "MANAGER"
    assert resp.json()["is_blocked"] is False


@pytest.mark.parametrize(
    "params",
    [
        {"skip": 2**63},
        {"limit": 0},
        {"limit": 101},
        {"q": ""},
        {"q": "a" * 101},
        {"q": "a\x00b"},
        {"role": "BOGUS"},
    ],
)
async def test_list_bounds_and_input_are_422(
    client: AsyncClient, base: SimpleNamespace, params: dict
) -> None:
    resp = await client.get("/api/v1/admin/users", params=params, headers=_auth(base.admin_token))

    assert resp.status_code == 422


@pytest.mark.parametrize("user_id", [0, 2**63])
async def test_patch_user_id_bounds_are_422(
    client: AsyncClient, base: SimpleNamespace, user_id: int
) -> None:
    resp = await client.patch(
        f"/api/v1/admin/users/{user_id}", json={"role": "MANAGER"}, headers=_auth(base.admin_token)
    )

    assert resp.status_code == 422


async def test_access_control(client: AsyncClient, base: SimpleNamespace) -> None:
    anon = await client.get("/api/v1/admin/users")
    assert anon.status_code == 401

    client_resp = await client.get("/api/v1/admin/users", headers=_auth(base.client_token))
    assert client_resp.status_code == 403

    manager_resp = await client.get("/api/v1/admin/users", headers=_auth(base.manager_token))
    assert manager_resp.status_code == 403

    blocked_resp = await client.get("/api/v1/admin/users", headers=_auth(base.blocked_admin_token))
    assert blocked_resp.status_code == 403


async def test_block_closes_open_panel(client: AsyncClient, base: SimpleNamespace) -> None:
    async with (
        _ws_http() as ws_http,
        aconnect_ws(f"{WS_PATH}?token={base.manager_token}", ws_http) as ws,
    ):
        await _wait_until(lambda: len(ws_manager._connections) == 1)

        resp = await client.patch(
            f"/api/v1/admin/users/{base.manager.id}",
            json={"is_blocked": True},
            headers=_auth(base.admin_token),
        )
        assert resp.status_code == 200

        assert await _expect_close(ws) == 4403


async def test_demotion_to_client_closes_open_panel(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    async with (
        _ws_http() as ws_http,
        aconnect_ws(f"{WS_PATH}?token={base.manager_token}", ws_http) as ws,
    ):
        await _wait_until(lambda: len(ws_manager._connections) == 1)

        resp = await client.patch(
            f"/api/v1/admin/users/{base.manager.id}",
            json={"role": "CLIENT"},
            headers=_auth(base.admin_token),
        )
        assert resp.status_code == 200

        assert await _expect_close(ws) == 4403


async def test_promotion_to_admin_keeps_open_panel(
    client: AsyncClient, base: SimpleNamespace
) -> None:
    async with (
        _ws_http() as ws_http,
        aconnect_ws(f"{WS_PATH}?token={base.manager_token}", ws_http) as ws,
    ):
        await _wait_until(lambda: len(ws_manager._connections) == 1)

        resp = await client.patch(
            f"/api/v1/admin/users/{base.manager.id}",
            json={"role": "ADMIN"},
            headers=_auth(base.admin_token),
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "ADMIN"

        await ws_manager.broadcast({"type": "ticket_created", "ticket": {"id": 1}})
        event = await _receive_json(ws)

    assert event["type"] == "ticket_created"
