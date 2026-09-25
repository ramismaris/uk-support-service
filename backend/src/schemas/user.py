from pydantic import BaseModel, ConfigDict

from src.core.constants import UserRole


class UserShortResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str | None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    max_user_id: int
    first_name: str
    last_name: str | None
    username: str | None
    phone: str | None
    role: UserRole
