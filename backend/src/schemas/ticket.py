from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from src.core.constants import TicketPriority, TicketStatus, TicketType
from src.schemas.file import FileResponse
from src.schemas.user import UserResponse, UserShortResponse
from src.services import ticket_rules


class CategoryShortResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str


class BuildingShortResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    address: str


class TicketListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: TicketType
    status: TicketStatus
    priority: TicketPriority
    description: str
    category: CategoryShortResponse | None
    building: BuildingShortResponse | None
    apartment: str | None
    client: UserShortResponse
    assignee: UserShortResponse | None
    created_at: datetime
    last_client_message_at: datetime | None
    staff_seen_at: datetime | None = Field(default=None, exclude=True)

    @computed_field
    @property
    def unread(self) -> bool:
        return ticket_rules.is_unread(self.last_client_message_at, self.staff_seen_at)


class StatusChangeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    from_status: TicketStatus | None
    to_status: TicketStatus
    changed_by: UserShortResponse | None
    comment: str | None
    created_at: datetime


class StatusChangeRequest(BaseModel):
    status: TicketStatus
    comment: str | None = None


class TicketDetailResponse(TicketListItemResponse):
    client: UserResponse
    contact_phone: str | None
    preferred_time: str | None
    rating: int | None
    closed_at: datetime | None
    files: list[FileResponse]
    history: list[StatusChangeResponse]
    allowed_statuses: list[TicketStatus]
