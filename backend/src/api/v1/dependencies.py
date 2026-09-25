from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import UserRole
from src.core.exceptions import ForbiddenException, UnauthorizedException
from src.db.session import get_db
from src.models.user import User
from src.services.auth_service import AuthService

security = HTTPBearer(auto_error=False)


async def get_current_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> str:
    if credentials is None:
        raise UnauthorizedException("Требуется авторизация")
    return credentials.credentials


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if credentials is None:
        raise UnauthorizedException("Требуется авторизация")
    return await AuthService(db).get_user_by_token(credentials.credentials)


async def require_staff(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    if user.role not in (UserRole.MANAGER, UserRole.ADMIN):
        raise ForbiddenException("Недостаточно прав")
    return user


async def require_admin(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    if user.role != UserRole.ADMIN:
        raise ForbiddenException("Недостаточно прав")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
StaffUser = Annotated[User, Depends(require_staff)]
AdminUser = Annotated[User, Depends(require_admin)]
