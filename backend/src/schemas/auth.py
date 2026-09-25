from pydantic import BaseModel, Field

from src.core.constants import BIGINT_MAX
from src.schemas.user import UserResponse


class MaxLoginRequest(BaseModel):
    init_data: str


class DevLoginRequest(BaseModel):
    max_user_id: int = Field(ge=1, le=BIGINT_MAX)


class TokenResponse(BaseModel):
    token: str
    user: UserResponse
