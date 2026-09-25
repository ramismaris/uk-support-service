from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.constants import UserRole
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
