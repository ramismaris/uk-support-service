from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import ContentKey, UserRole
from src.core.security import hash_token
from src.core.texts import THEME_NOT_SET
from src.repositories.auth_token_repository import AuthTokenRepository
from src.repositories.content_block_repository import ContentBlockRepository
from src.repositories.user_repository import UserRepository

THEME = {
    "company_name": "УК «Наш дом»",
    "primary_color": "#1E88E5",
    "logo_file_id": None,
}


async def _issue_token(db: AsyncSession, user) -> str:
    token = f"theme-token-{user.id}"
    await AuthTokenRepository(db).create(
        user.id, hash_token(token), datetime.now(UTC) + timedelta(days=1)
    )
    return token


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def tokens(db: AsyncSession) -> dict[str, str]:
    users = UserRepository(db)
    client = await users.create(max_user_id=3100003, first_name="Мария")
    manager = await users.create(max_user_id=3100002, first_name="Игорь", role=UserRole.MANAGER)
    admin = await users.create(max_user_id=3100001, first_name="Анна", role=UserRole.ADMIN)
    client_token = await _issue_token(db, client)
    manager_token = await _issue_token(db, manager)
    admin_token = await _issue_token(db, admin)
    await db.commit()
    return {
        "client": client_token,
        "manager": manager_token,
        "admin": admin_token,
    }


@pytest.fixture
async def theme_seeded(db: AsyncSession) -> None:
    await ContentBlockRepository(db).create(ContentKey.THEME, THEME)
    await db.commit()


@pytest.mark.parametrize("role", ["client", "manager", "admin"])
async def test_theme_available_for_all_roles(
    client: AsyncClient, tokens: dict[str, str], theme_seeded: None, role: str
) -> None:
    resp = await client.get("/api/v1/theme", headers=_auth(tokens[role]))

    assert resp.status_code == 200
    assert resp.json() == {**THEME, "logo_url": None}


async def test_theme_missing_returns_404(client: AsyncClient, tokens: dict[str, str]) -> None:
    resp = await client.get("/api/v1/theme", headers=_auth(tokens["client"]))

    assert resp.status_code == 404
    assert resp.json() == {"detail": THEME_NOT_SET}


async def test_theme_broken_returns_404(
    client: AsyncClient, db: AsyncSession, tokens: dict[str, str]
) -> None:
    await ContentBlockRepository(db).create(ContentKey.THEME, {"company_name": "УК"})
    await db.commit()

    resp = await client.get("/api/v1/theme", headers=_auth(tokens["client"]))

    assert resp.status_code == 404
    assert resp.json() == {"detail": THEME_NOT_SET}


async def test_theme_requires_token(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/theme")

    assert resp.status_code == 401
