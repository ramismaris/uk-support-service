from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from src.core.constants import TicketStatus, TicketType
from src.schemas.dashboard import (
    CountMetric,
    DashboardCategory,
    DashboardDay,
    DashboardNow,
    DashboardQuestions,
    DashboardResponse,
    DashboardSla,
    DashboardSummary,
    RatingMetric,
    ValueMetric,
)
from src.services.ticket_rules import OPEN_STATUSES


@dataclass(frozen=True)
class TicketFacts:
    type: TicketType
    status: TicketStatus
    category_id: int | None
    category_title: str | None
    category_sort_order: int | None
    created_at: datetime
    closed_at: datetime | None
    reacted_at: datetime | None
    rating: int | None
    building_id: int | None = None
    building_address: str | None = None
    assignee_id: int | None = None


@dataclass(frozen=True)
class PeriodBounds:
    date_from: date
    date_to: date
    start: datetime
    previous_start: datetime


@dataclass(frozen=True)
class WindowMetrics:
    created: int
    closed: int
    reaction_minutes: float | None
    resolution_hours: float | None
    reaction_on_time: float | None
    resolution_on_time: float | None
    rating: float | None
    rating_count: int


def period_bounds(now: datetime, days: int, tz: ZoneInfo) -> PeriodBounds:
    today = now.astimezone(tz).date()
    date_from = today - timedelta(days=days - 1)
    start = datetime.combine(date_from, time.min, tzinfo=tz)
    previous_start = datetime.combine(date_from - timedelta(days=days), time.min, tzinfo=tz)
    return PeriodBounds(
        date_from=date_from,
        date_to=today,
        start=start,
        previous_start=previous_start,
    )


def build_dashboard(
    facts: list[TicketFacts],
    *,
    now: datetime,
    days: int,
    tz: ZoneInfo,
    reaction: timedelta,
    resolution: timedelta,
) -> DashboardResponse:
    bounds = period_bounds(now, days, tz)
    current = window_metrics(
        facts,
        bounds.start,
        now,
        previous=False,
        now=now,
        reaction=reaction,
        resolution=resolution,
    )
    previous = window_metrics(
        facts,
        bounds.previous_start,
        bounds.start,
        previous=True,
        now=now,
        reaction=reaction,
        resolution=resolution,
    )

    return DashboardResponse(
        period_days=days,
        date_from=bounds.date_from,
        date_to=bounds.date_to,
        sla=DashboardSla(
            reaction_hours=_hours(reaction),
            resolution_hours=_hours(resolution),
        ),
        now=_now_block(facts, now=now, reaction=reaction, resolution=resolution),
        summary=DashboardSummary(
            created=CountMetric(value=current.created, previous=previous.created),
            closed=CountMetric(value=current.closed, previous=previous.closed),
            reaction_minutes=ValueMetric(
                value=round_optional(current.reaction_minutes, 1),
                previous=round_optional(previous.reaction_minutes, 1),
            ),
            resolution_hours=ValueMetric(
                value=round_optional(current.resolution_hours, 1),
                previous=round_optional(previous.resolution_hours, 1),
            ),
            reaction_on_time=ValueMetric(
                value=round_optional(current.reaction_on_time, 3),
                previous=round_optional(previous.reaction_on_time, 3),
            ),
            resolution_on_time=ValueMetric(
                value=round_optional(current.resolution_on_time, 3),
                previous=round_optional(previous.resolution_on_time, 3),
            ),
            rating=RatingMetric(
                value=round_optional(current.rating, 2),
                previous=round_optional(previous.rating, 2),
                count=current.rating_count,
            ),
        ),
        daily=_daily(facts, bounds, now=now, tz=tz),
        categories=_categories(facts, bounds, now=now),
        questions=_questions(facts, bounds, now=now),
    )


def window_metrics(
    facts: list[TicketFacts],
    start: datetime,
    end: datetime,
    *,
    previous: bool,
    now: datetime,
    reaction: timedelta,
    resolution: timedelta,
) -> WindowMetrics:
    created = 0
    closed = 0
    reaction_minutes: list[float] = []
    resolution_hours: list[float] = []
    reaction_on_time = 0
    reaction_late = 0
    resolution_on_time = 0
    ratings: list[int] = []

    for fact in facts:
        if _within(fact.created_at, start, end, end_inclusive=not previous):
            created += 1
            if fact.reacted_at is not None:
                delay = fact.reacted_at - fact.created_at
                reaction_minutes.append(delay.total_seconds() / 60)
                if delay <= reaction:
                    reaction_on_time += 1
                else:
                    reaction_late += 1
            elif now - fact.created_at > reaction:
                reaction_late += 1

        if (
            fact.status == TicketStatus.CLOSED
            and fact.closed_at is not None
            and _within(fact.closed_at, start, end, end_inclusive=not previous)
        ):
            closed += 1
            taken = fact.closed_at - fact.created_at
            resolution_hours.append(taken.total_seconds() / 3600)
            if taken <= resolution:
                resolution_on_time += 1
            if fact.rating is not None:
                ratings.append(fact.rating)

    reaction_total = reaction_on_time + reaction_late
    return WindowMetrics(
        created=created,
        closed=closed,
        reaction_minutes=_mean(reaction_minutes),
        resolution_hours=_mean(resolution_hours),
        reaction_on_time=reaction_on_time / reaction_total if reaction_total else None,
        resolution_on_time=resolution_on_time / closed if closed else None,
        rating=_mean(ratings),
        rating_count=len(ratings),
    )


def is_overdue(
    fact: TicketFacts,
    *,
    now: datetime,
    reaction: timedelta,
    resolution: timedelta,
) -> bool:
    if fact.status not in OPEN_STATUSES:
        return False
    age = now - fact.created_at
    return (fact.status == TicketStatus.NEW and age > reaction) or age > resolution


def _now_block(
    facts: list[TicketFacts],
    *,
    now: datetime,
    reaction: timedelta,
    resolution: timedelta,
) -> DashboardNow:
    by_status = {status: 0 for status in OPEN_STATUSES}
    overdue = 0
    for fact in facts:
        if fact.status in by_status:
            by_status[fact.status] += 1
        if is_overdue(fact, now=now, reaction=reaction, resolution=resolution):
            overdue += 1
    return DashboardNow(
        new=by_status[TicketStatus.NEW],
        in_progress=by_status[TicketStatus.IN_PROGRESS],
        waiting_client=by_status[TicketStatus.WAITING_CLIENT],
        overdue=overdue,
    )


def _daily(
    facts: list[TicketFacts],
    bounds: PeriodBounds,
    *,
    now: datetime,
    tz: ZoneInfo,
) -> list[DashboardDay]:
    days = (bounds.date_to - bounds.date_from).days + 1
    created_counts = [0] * days
    closed_counts = [0] * len(created_counts)
    for fact in facts:
        if _within(fact.created_at, bounds.start, now, end_inclusive=True):
            index = (fact.created_at.astimezone(tz).date() - bounds.date_from).days
            if 0 <= index < len(created_counts):
                created_counts[index] += 1
        if (
            fact.status == TicketStatus.CLOSED
            and fact.closed_at is not None
            and _within(fact.closed_at, bounds.start, now, end_inclusive=True)
        ):
            index = (fact.closed_at.astimezone(tz).date() - bounds.date_from).days
            if 0 <= index < len(closed_counts):
                closed_counts[index] += 1

    return [
        DashboardDay(
            date=bounds.date_from + timedelta(days=index),
            created=created_counts[index],
            closed=closed_counts[index],
        )
        for index in range(len(created_counts))
    ]


def _categories(
    facts: list[TicketFacts],
    bounds: PeriodBounds,
    *,
    now: datetime,
) -> list[DashboardCategory]:
    created: dict[int, int] = {}
    resolution: dict[int, list[float]] = {}
    titles: dict[int, str] = {}
    orders: dict[int, int | None] = {}

    for fact in facts:
        if fact.type != TicketType.REQUEST or fact.category_id is None:
            continue
        in_created = _within(fact.created_at, bounds.start, now, end_inclusive=True)
        in_closed = (
            fact.status == TicketStatus.CLOSED
            and fact.closed_at is not None
            and _within(fact.closed_at, bounds.start, now, end_inclusive=True)
        )
        if not in_created and not in_closed:
            continue
        titles[fact.category_id] = fact.category_title or ""
        orders[fact.category_id] = fact.category_sort_order
        if in_created:
            created[fact.category_id] = created.get(fact.category_id, 0) + 1
        if in_closed:
            hours = (fact.closed_at - fact.created_at).total_seconds() / 3600
            resolution.setdefault(fact.category_id, []).append(hours)

    # Ties keep the category order of the bot: titles start with emoji, so they sort by code point.
    ids = sorted(
        set(created) | set(resolution),
        key=lambda category_id: (
            -created.get(category_id, 0),
            orders[category_id] or 0,
            titles[category_id],
        ),
    )
    return [
        DashboardCategory(
            category_id=category_id,
            title=titles[category_id],
            created=created.get(category_id, 0),
            resolution_hours=round_optional(_mean(resolution.get(category_id, [])), 1),
        )
        for category_id in ids
    ]


def _questions(
    facts: list[TicketFacts],
    bounds: PeriodBounds,
    *,
    now: datetime,
) -> DashboardQuestions:
    created = 0
    resolution: list[float] = []
    for fact in facts:
        if fact.type != TicketType.QUESTION:
            continue
        if _within(fact.created_at, bounds.start, now, end_inclusive=True):
            created += 1
        if (
            fact.status == TicketStatus.CLOSED
            and fact.closed_at is not None
            and _within(fact.closed_at, bounds.start, now, end_inclusive=True)
        ):
            resolution.append((fact.closed_at - fact.created_at).total_seconds() / 3600)
    return DashboardQuestions(
        created=created,
        resolution_hours=round_optional(_mean(resolution), 1),
    )


def _within(ts: datetime, start: datetime, end: datetime, *, end_inclusive: bool) -> bool:
    if end_inclusive:
        return start <= ts <= end
    return start <= ts < end


def _mean(values: list[float] | list[int]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def round_optional(value: float | None, digits: int) -> float | None:
    if value is None:
        return None
    return round(value, digits)


def _hours(delta: timedelta) -> int:
    return int(delta / timedelta(hours=1))
