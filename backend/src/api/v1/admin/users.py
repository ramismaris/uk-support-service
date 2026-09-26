from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import AdminUser
from src.core.constants import BIGINT_MAX, UserRole
from src.db.session import get_db
from src.schemas.common import NoNul, PaginatedResponse
from src.schemas.user import AdminUserResponse, UserUpdateRequest
from src.services.user_service import UserService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=PaginatedResponse[AdminUserResponse])
async def list_users(
    admin: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    role: Annotated[list[UserRole] | None, Query()] = None,
    is_blocked: bool | None = None,
    q: Annotated[Annotated[str, NoNul] | None, Query(min_length=1, max_length=100)] = None,
    skip: Annotated[int, Query(ge=0, le=BIGINT_MAX)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> PaginatedResponse[AdminUserResponse]:
    users, total = await UserService(db).list_for_admin(
        roles=role,
        is_blocked=is_blocked,
        q=q,
        skip=skip,
        limit=limit,
    )
    return PaginatedResponse(
        total=total,
        items=[AdminUserResponse.model_validate(user) for user in users],
    )


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: Annotated[int, Path(ge=1, le=BIGINT_MAX)],
    body: UserUpdateRequest,
    admin: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminUserResponse:
    user = await UserService(db).update_by_admin(
        user_id,
        admin,
        role=body.role,
        is_blocked=body.is_blocked,
    )
    return AdminUserResponse.model_validate(user)
