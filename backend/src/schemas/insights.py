from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class InsightItem(BaseModel):
    kind: Literal["fact", "observation", "warning"]
    text: str


class InsightsResponse(BaseModel):
    status: Literal["ok", "disabled", "unavailable"]
    period_days: int
    generated_at: datetime | None
    items: list[InsightItem]
