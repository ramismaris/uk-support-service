from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.core.constants import SenderType
from src.schemas.file import FileResponse
from src.schemas.user import UserShortResponse


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    sender_type: SenderType
    author: UserShortResponse | None
    text: str | None
    files: list[FileResponse]
    created_at: datetime
