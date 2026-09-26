from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import UserRole
from src.models.user import User


def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_max_user_id(self, max_user_id: int) -> User | None:
        result = await self.db.execute(select(User).where(User.max_user_id == max_user_id))
        return result.scalar_one_or_none()

    async def list_staff(self) -> list[User]:
        result = await self.db.execute(
            select(User)
            .where(User.role.in_([UserRole.MANAGER, UserRole.ADMIN]), User.is_blocked.is_(False))
            .order_by(User.id)
        )
        return list(result.scalars().all())

    async def list(
        self,
        *,
        roles: list[UserRole] | None = None,
        is_blocked: bool | None = None,
        search: str | None = None,
        max_user_id: int | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[User]:
        query = self._filtered(
            roles=roles,
            is_blocked=is_blocked,
            search=search,
            max_user_id=max_user_id,
        )
        query = query.order_by(User.id.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count(
        self,
        *,
        roles: list[UserRole] | None = None,
        is_blocked: bool | None = None,
        search: str | None = None,
        max_user_id: int | None = None,
    ) -> int:
        query = self._filtered(
            roles=roles,
            is_blocked=is_blocked,
            search=search,
            max_user_id=max_user_id,
        )
        result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        return result.scalar_one()

    def _filtered(
        self,
        *,
        roles: list[UserRole] | None,
        is_blocked: bool | None,
        search: str | None,
        max_user_id: int | None,
    ):
        query = select(User)
        if roles is not None:
            query = query.where(User.role.in_(roles))
        if is_blocked is not None:
            query = query.where(User.is_blocked.is_(is_blocked))

        matches = []
        if search is not None:
            pattern = f"%{_escape_like(search)}%"
            name = func.concat_ws(" ", User.first_name, User.last_name)
            matches.extend(
                [
                    name.ilike(pattern, escape="\\"),
                    User.username.ilike(pattern, escape="\\"),
                    User.phone.ilike(pattern, escape="\\"),
                ]
            )
        if max_user_id is not None:
            matches.append(User.max_user_id == max_user_id)
        if matches:
            query = query.where(or_(*matches))
        return query

    async def create(
        self,
        max_user_id: int,
        first_name: str,
        last_name: str | None = None,
        username: str | None = None,
        role: UserRole = UserRole.CLIENT,
        phone: str | None = None,
    ) -> User:
        user = User(
            max_user_id=max_user_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
            role=role,
            phone=phone,
        )
        self.db.add(user)
        await self.db.flush()
        return user
