from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import UserRole
from src.models.user import User


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_max_user_id(self, max_user_id: int) -> User | None:
        result = await self.db.execute(select(User).where(User.max_user_id == max_user_id))
        return result.scalar_one_or_none()

    async def create(
        self,
        max_user_id: int,
        first_name: str,
        last_name: str | None = None,
        username: str | None = None,
        role: UserRole = UserRole.CLIENT,
    ) -> User:
        user = User(
            max_user_id=max_user_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
            role=role,
        )
        self.db.add(user)
        await self.db.flush()
        return user
