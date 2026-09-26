import re
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.constants import BIGINT_MAX, UserRole
from src.core.exceptions import AppException, NotFoundException
from src.core.texts import USER_CANNOT_CHANGE_SELF, USER_CONFIG_ADMIN, USER_NOT_FOUND
from src.core.ws_manager import WS_FORBIDDEN, ws_manager
from src.models.user import User
from src.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.users = UserRepository(db)

    async def sync_from_max(
        self,
        max_user_id: int,
        first_name: str,
        last_name: str | None = None,
        username: str | None = None,
    ) -> User:
        user = await self.users.get_by_max_user_id(max_user_id)
        is_admin = max_user_id in settings.admin_max_user_ids

        if user is None:
            user = await self.users.create(
                max_user_id=max_user_id,
                first_name=first_name,
                last_name=last_name or None,
                username=username or None,
                role=UserRole.ADMIN if is_admin else UserRole.CLIENT,
            )
        else:
            user.first_name = first_name
            user.last_name = last_name or None
            user.username = username or None
            if is_admin and user.role != UserRole.ADMIN:
                user.role = UserRole.ADMIN

        user.last_seen_at = datetime.now(UTC)
        await self.db.commit()
        return user

    async def list_for_admin(
        self,
        *,
        roles: list[UserRole] | None,
        is_blocked: bool | None,
        q: str | None,
        skip: int,
        limit: int,
    ) -> tuple[list[User], int]:
        search = q.strip() if q else None
        if search == "":
            search = None

        max_user_id = None
        if search is not None and re.fullmatch(r"[0-9]{1,19}", search):
            numeric = int(search)
            if numeric <= BIGINT_MAX:
                max_user_id = numeric

        users = await self.users.list(
            roles=roles,
            is_blocked=is_blocked,
            search=search,
            max_user_id=max_user_id,
            skip=skip,
            limit=limit,
        )
        total = await self.users.count(
            roles=roles,
            is_blocked=is_blocked,
            search=search,
            max_user_id=max_user_id,
        )
        return users, total

    async def update_by_admin(
        self,
        user_id: int,
        admin: User,
        *,
        role: UserRole | None,
        is_blocked: bool | None,
    ) -> User:
        user = await self.users.get_by_id(user_id)
        if user is None:
            raise NotFoundException(USER_NOT_FOUND)

        loses_admin = (role is not None and role != UserRole.ADMIN) or is_blocked is True
        if loses_admin:
            if user.id == admin.id:
                raise AppException(USER_CANNOT_CHANGE_SELF, status_code=409)
            if user.max_user_id in settings.admin_max_user_ids:
                raise AppException(USER_CONFIG_ADMIN, status_code=409)

        if role is not None:
            user.role = role
        if is_blocked is not None:
            user.is_blocked = is_blocked
        await self.db.commit()

        if user.is_blocked or user.role == UserRole.CLIENT:
            await ws_manager.close_user(user.id, WS_FORBIDDEN)

        return user
