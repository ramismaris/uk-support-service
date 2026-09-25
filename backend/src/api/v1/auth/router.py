from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import CurrentUser, get_current_token
from src.db.session import get_db
from src.schemas.auth import DevLoginRequest, MaxLoginRequest, TokenResponse
from src.schemas.user import UserResponse
from src.services.auth_service import AuthService

router = APIRouter(tags=["auth"])


@router.post("/auth/max", response_model=TokenResponse)
async def login_with_max(
    payload: MaxLoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    token, user = await AuthService(db).login_with_init_data(payload.init_data)
    return TokenResponse(token=token, user=UserResponse.model_validate(user))


@router.post("/auth/dev", response_model=TokenResponse)
async def dev_login(
    payload: DevLoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    token, user = await AuthService(db).dev_login(payload.max_user_id)
    return TokenResponse(token=token, user=UserResponse.model_validate(user))


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    token: Annotated[str, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    await AuthService(db).logout(token)


@router.get("/me", response_model=UserResponse)
async def read_me(current_user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(current_user)
