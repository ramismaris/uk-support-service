import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from urllib.parse import urlencode

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.security import hash_token
from src.repositories.auth_token_repository import AuthTokenRepository
from src.repositories.user_repository import UserRepository

BOT_TOKEN = "test-bot-token"


def _sign(fields: dict[str, str], bot_token: str = BOT_TOKEN) -> str:
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    signed = {
        **fields,
        "hash": hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest(),
    }
    return urlencode(signed)


def _init_data(
    max_user_id: int = 42,
    bot_token: str = BOT_TOKEN,
    auth_date: datetime | None = None,
) -> str:
    fields = {
        "auth_date": str(int((auth_date or datetime.now(UTC)).timestamp())),
        "query_id": "AAA",
        "user": json.dumps(
            {
                "id": max_user_id,
                "first_name": "Иван",
                "last_name": "Петров",
                "username": "ivan",
            },
            ensure_ascii=False,
        ),
    }
    return _sign(fields, bot_token)


async def test_max_login_issues_working_token(client: AsyncClient):
    init_data = _init_data(max_user_id=500)

    with (
        patch.object(settings, "bot_token", BOT_TOKEN),
        patch.object(settings, "admin_max_user_ids", []),
    ):
        login = await client.post("/api/v1/auth/max", json={"init_data": init_data})

    assert login.status_code == 200
    body = login.json()
    assert body["token"]
    assert body["user"]["max_user_id"] == 500
    assert body["user"]["role"] == "CLIENT"

    me = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {body['token']}"})

    assert me.status_code == 200
    assert me.json()["max_user_id"] == 500


async def test_max_login_bootstraps_admin(client: AsyncClient):
    init_data = _init_data(max_user_id=501)

    with (
        patch.object(settings, "bot_token", BOT_TOKEN),
        patch.object(settings, "admin_max_user_ids", [501]),
    ):
        login = await client.post("/api/v1/auth/max", json={"init_data": init_data})

    assert login.status_code == 200
    assert login.json()["user"]["role"] == "ADMIN"


async def test_max_login_rejects_invalid_init_data(client: AsyncClient):
    init_data = _init_data(bot_token="wrong-token")

    with patch.object(settings, "bot_token", BOT_TOKEN):
        resp = await client.post("/api/v1/auth/max", json={"init_data": init_data})

    assert resp.status_code == 401


async def test_max_login_rejects_non_ascii_hash(client: AsyncClient):
    init_data = urlencode({"auth_date": "1700000000", "user": "{}", "hash": "абв"})

    with patch.object(settings, "bot_token", BOT_TOKEN):
        resp = await client.post("/api/v1/auth/max", json={"init_data": init_data})

    assert resp.status_code == 401


async def test_max_login_rejects_expired_init_data(client: AsyncClient):
    init_data = _init_data(auth_date=datetime.now(UTC) - timedelta(hours=25))

    with patch.object(settings, "bot_token", BOT_TOKEN):
        resp = await client.post("/api/v1/auth/max", json={"init_data": init_data})

    assert resp.status_code == 401


async def test_me_requires_token(client: AsyncClient):
    resp = await client.get("/api/v1/me")

    assert resp.status_code == 401


async def test_expired_token_is_rejected(client: AsyncClient, db: AsyncSession):
    user = await UserRepository(db).create(max_user_id=504, first_name="Тест")
    await db.flush()
    token = "expired-token"
    await AuthTokenRepository(db).create(
        user.id, hash_token(token), datetime.now(UTC) - timedelta(days=1)
    )
    await db.commit()

    me = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})

    assert me.status_code == 401


async def test_logout_invalidates_token(client: AsyncClient):
    init_data = _init_data(max_user_id=502)

    with (
        patch.object(settings, "bot_token", BOT_TOKEN),
        patch.object(settings, "admin_max_user_ids", []),
    ):
        login = await client.post("/api/v1/auth/max", json={"init_data": init_data})

    headers = {"Authorization": f"Bearer {login.json()['token']}"}

    logout = await client.post("/api/v1/auth/logout", headers=headers)
    assert logout.status_code == 204

    me = await client.get("/api/v1/me", headers=headers)
    assert me.status_code == 401


async def test_dev_login_disabled_returns_404(client: AsyncClient):
    with patch.object(settings, "dev_auth", False):
        resp = await client.post("/api/v1/auth/dev", json={"max_user_id": 1})

    assert resp.status_code == 404


async def test_dev_login_enabled_returns_token(client: AsyncClient, db: AsyncSession):
    user = await UserRepository(db).create(max_user_id=777, first_name="Тест")
    await db.commit()

    with patch.object(settings, "dev_auth", True):
        login = await client.post("/api/v1/auth/dev", json={"max_user_id": 777})

    assert login.status_code == 200

    me = await client.get(
        "/api/v1/me", headers={"Authorization": f"Bearer {login.json()['token']}"}
    )

    assert me.status_code == 200
    assert me.json()["id"] == user.id


async def test_blocked_user_cannot_login(client: AsyncClient, db: AsyncSession):
    user = await UserRepository(db).create(max_user_id=888, first_name="Блок")
    user.is_blocked = True
    await db.commit()

    with patch.object(settings, "dev_auth", True):
        resp = await client.post("/api/v1/auth/dev", json={"max_user_id": 888})

    assert resp.status_code == 403


async def test_blocked_user_token_is_rejected(client: AsyncClient, db: AsyncSession):
    init_data = _init_data(max_user_id=503)

    with (
        patch.object(settings, "bot_token", BOT_TOKEN),
        patch.object(settings, "admin_max_user_ids", []),
    ):
        login = await client.post("/api/v1/auth/max", json={"init_data": init_data})

    user = await UserRepository(db).get_by_max_user_id(503)
    user.is_blocked = True
    await db.commit()

    me = await client.get(
        "/api/v1/me", headers={"Authorization": f"Bearer {login.json()['token']}"}
    )

    assert me.status_code == 403
