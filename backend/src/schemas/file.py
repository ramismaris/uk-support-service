from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, computed_field

from src.core.security import build_file_url


class FileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mime: str
    size: int
    original_name: str | None

    @computed_field
    @property
    def url(self) -> str:
        return build_file_url(self.id, datetime.now(UTC))
