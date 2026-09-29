from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, computed_field

from src.core.constants import BIGINT_MAX, BroadcastStatus
from src.core.security import build_file_url
from src.schemas.content import ContentText, FileId
from src.schemas.ticket import BuildingShortResponse

BUILDING_IDS_MAX = 100

BuildingId = Annotated[int, Field(ge=1, le=BIGINT_MAX)]
BuildingIds = Annotated[list[BuildingId], Field(min_length=1, max_length=BUILDING_IDS_MAX)]


class BroadcastCreateRequest(BaseModel):
    text: ContentText
    file_id: FileId | None = None
    # None means everyone; an empty list is rejected instead of meaning everyone.
    building_ids: BuildingIds | None = None


class BroadcastAuthorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str | None


class BroadcastResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    author: BroadcastAuthorResponse
    text: str
    file_id: int | None = Field(default=None, exclude=True)
    buildings: list[BuildingShortResponse]
    status: BroadcastStatus
    recipients_total: int
    delivered_count: int
    failed_count: int
    created_at: datetime
    finished_at: datetime | None

    @computed_field
    @property
    def file_url(self) -> str | None:
        if self.file_id is None:
            return None
        return build_file_url(self.file_id, datetime.now(UTC))


class AudienceResponse(BaseModel):
    count: int
