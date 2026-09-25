from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.auth_token import AuthToken


class AuthTokenRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: int, token_hash: str, expires_at: datetime) -> AuthToken:
        auth_token = AuthToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self.db.add(auth_token)
        await self.db.flush()
        return auth_token

    async def get_by_token_hash(self, token_hash: str) -> AuthToken | None:
        result = await self.db.execute(select(AuthToken).where(AuthToken.token_hash == token_hash))
        return result.scalar_one_or_none()

    async def delete_by_token_hash(self, token_hash: str) -> None:
        await self.db.execute(delete(AuthToken).where(AuthToken.token_hash == token_hash))
