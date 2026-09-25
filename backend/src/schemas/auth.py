from pydantic import BaseModel

from src.schemas.user import UserResponse


class MaxLoginRequest(BaseModel):
    init_data: str


class DevLoginRequest(BaseModel):
    max_user_id: int


class TokenResponse(BaseModel):
    token: str
    user: UserResponse
