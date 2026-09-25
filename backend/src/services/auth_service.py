from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.exceptions import ForbiddenException, NotFoundException, UnauthorizedException
from src.core.security import generate_token, hash_token, validate_init_data
from src.models.user import User
from src.repositories.auth_token_repository import AuthTokenRepository
from src.repositories.user_repository import UserRepository
from src.services.user_service import UserService


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.users = UserRepository(db)
        self.tokens = AuthTokenRepository(db)
        self.user_service = UserService(db)

    async def login_with_init_data(self, init_data: str) -> tuple[str, User]:
        max_user = validate_init_data(init_data, settings.bot_token, datetime.now(UTC))
        user = await self.user_service.sync_from_max(
            max_user_id=max_user.max_user_id,
            first_name=max_user.first_name,
            last_name=max_user.last_name,
            username=max_user.username,
        )
        if user.is_blocked:
            raise ForbiddenException("Пользователь заблокирован")
        return await self._issue_token(user)

    async def dev_login(self, max_user_id: int) -> tuple[str, User]:
        if not settings.dev_auth:
            raise NotFoundException()
        user = await self.users.get_by_max_user_id(max_user_id)
        if user is None:
            raise NotFoundException("Пользователь не найден")
        if user.is_blocked:
            raise ForbiddenException("Пользователь заблокирован")
        return await self._issue_token(user)

    async def logout(self, token: str) -> None:
        await self.tokens.delete_by_token_hash(hash_token(token))
        await self.db.commit()

    async def get_user_by_token(self, token: str) -> User:
        auth_token = await self.tokens.get_by_token_hash(hash_token(token))
        if auth_token is None:
            raise UnauthorizedException("Токен не найден")
        if auth_token.expires_at < datetime.now(UTC):
            raise UnauthorizedException("Токен истёк")
        user = await self.users.get_by_id(auth_token.user_id)
        if user is None:
            raise UnauthorizedException("Пользователь не найден")
        if user.is_blocked:
            raise ForbiddenException("Пользователь заблокирован")
        return user

    async def _issue_token(self, user: User) -> tuple[str, User]:
        token = generate_token()
        expires_at = datetime.now(UTC) + timedelta(days=settings.auth_token_expire_days)
        await self.tokens.create(user.id, hash_token(token), expires_at)
        await self.db.commit()
        return token, user
