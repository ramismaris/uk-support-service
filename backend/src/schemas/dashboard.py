from datetime import date

from pydantic import BaseModel


class DashboardSla(BaseModel):
    reaction_hours: int
    resolution_hours: int


class DashboardNow(BaseModel):
    new: int
    in_progress: int
    waiting_client: int
    overdue: int


class CountMetric(BaseModel):
    value: int
    previous: int


class ValueMetric(BaseModel):
    value: float | None
    previous: float | None


class RatingMetric(BaseModel):
    value: float | None
    previous: float | None
    count: int


class DashboardSummary(BaseModel):
    created: CountMetric
    closed: CountMetric
    reaction_minutes: ValueMetric
    resolution_hours: ValueMetric
    reaction_on_time: ValueMetric
    resolution_on_time: ValueMetric
    rating: RatingMetric


class DashboardDay(BaseModel):
    date: date
    created: int
    closed: int


class DashboardCategory(BaseModel):
    category_id: int
    title: str
    created: int
    resolution_hours: float | None


class DashboardQuestions(BaseModel):
    created: int
    resolution_hours: float | None


class DashboardResponse(BaseModel):
    period_days: int
    date_from: date
    date_to: date
    sla: DashboardSla
    now: DashboardNow
    summary: DashboardSummary
    daily: list[DashboardDay]
    categories: list[DashboardCategory]
    questions: DashboardQuestions
