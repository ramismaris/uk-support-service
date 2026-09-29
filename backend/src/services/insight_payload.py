from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from src.core.constants import TicketType
from src.schemas.dashboard import DashboardResponse
from src.services.dashboard import (
    TicketFacts,
    WindowMetrics,
    is_overdue,
    period_bounds,
    round_optional,
    window_metrics,
)
from src.services.ticket_rules import OPEN_STATUSES

MAX_BUILDINGS = 10
MAX_MANAGERS = 10


@dataclass(frozen=True)
class InsightPayload:
    data: dict[str, Any]
    manager_refs: dict[str, int]


def build_insight_payload(
    facts: list[TicketFacts],
    dashboard: DashboardResponse,
    *,
    now: datetime,
    days: int,
    tz: ZoneInfo,
    reaction: timedelta,
    resolution: timedelta,
) -> InsightPayload:
    bounds = period_bounds(now, days, tz)
    start = bounds.start
    previous_start = bounds.previous_start

    dumped = dashboard.model_dump(mode="json")
    data: dict[str, Any] = {
        "period_days": dumped["period_days"],
        "sla": dumped["sla"],
        "now": dumped["now"],
        "summary": dumped["summary"],
        "daily": dumped["daily"],
        "questions": dumped["questions"],
    }

    data["categories"] = _categories(
        facts,
        start,
        now,
        previous_start,
        reaction=reaction,
        resolution=resolution,
    )
    data["buildings"] = _buildings(
        facts,
        start,
        now,
        previous_start,
        reaction=reaction,
        resolution=resolution,
    )
    managers, manager_refs = _managers(
        facts,
        dashboard,
        start,
        now,
        reaction=reaction,
        resolution=resolution,
    )
    data["managers"] = managers

    return InsightPayload(data=data, manager_refs=manager_refs)


def _categories(
    facts: list[TicketFacts],
    start: datetime,
    now: datetime,
    previous_start: datetime,
    *,
    reaction: timedelta,
    resolution: timedelta,
) -> list[dict[str, Any]]:
    by_category: dict[int, list[TicketFacts]] = {}
    for fact in facts:
        if fact.type != TicketType.REQUEST or fact.category_id is None:
            continue
        by_category.setdefault(fact.category_id, []).append(fact)

    rows: list[dict[str, Any]] = []
    for slice_facts in by_category.values():
        current = window_metrics(
            slice_facts,
            start,
            now,
            previous=False,
            now=now,
            reaction=reaction,
            resolution=resolution,
        )
        previous = window_metrics(
            slice_facts,
            previous_start,
            start,
            previous=True,
            now=now,
            reaction=reaction,
            resolution=resolution,
        )
        if current.created == 0 and previous.created == 0:
            continue
        rows.append(
            {
                "title": _title(slice_facts),
                "created": current.created,
                "previous_created": previous.created,
                "resolution_hours": round_optional(current.resolution_hours, 1),
            }
        )

    total_created = sum(row["created"] for row in rows)
    rows.sort(key=lambda row: (-row["created"], -row["previous_created"], row["title"]))
    return [
        {
            "title": row["title"],
            "created": row["created"],
            "previous_created": row["previous_created"],
            "share": round_optional(row["created"] / total_created, 3) if total_created else None,
            "growth": (
                round_optional(row["created"] / row["previous_created"], 1)
                if row["previous_created"]
                else None
            ),
            "resolution_hours": row["resolution_hours"],
        }
        for row in rows
    ]


def _buildings(
    facts: list[TicketFacts],
    start: datetime,
    now: datetime,
    previous_start: datetime,
    *,
    reaction: timedelta,
    resolution: timedelta,
) -> list[dict[str, Any]]:
    by_building: dict[int, list[TicketFacts]] = {}
    for fact in facts:
        if fact.building_id is None:
            continue
        by_building.setdefault(fact.building_id, []).append(fact)

    groups: list[tuple[str, list[TicketFacts], WindowMetrics, WindowMetrics, int, int]] = []
    for slice_facts in by_building.values():
        address = next(
            (fact.building_address for fact in slice_facts if fact.building_address is not None),
            None,
        )
        if address is None:
            continue
        current = window_metrics(
            slice_facts,
            start,
            now,
            previous=False,
            now=now,
            reaction=reaction,
            resolution=resolution,
        )
        previous = window_metrics(
            slice_facts,
            previous_start,
            start,
            previous=True,
            now=now,
            reaction=reaction,
            resolution=resolution,
        )
        open_count = sum(1 for fact in slice_facts if fact.status in OPEN_STATUSES)
        overdue = sum(
            1
            for fact in slice_facts
            if is_overdue(fact, now=now, reaction=reaction, resolution=resolution)
        )
        groups.append((address, slice_facts, current, previous, open_count, overdue))

    total_created = sum(current.created for _, _, current, _, _, _ in groups)
    listed = [
        group for group in groups if group[2].created > 0 or group[3].created > 0 or group[4] > 0
    ]
    listed.sort(key=lambda group: (-group[2].created, -group[3].created, group[0]))

    return [
        {
            "address": address,
            "created": current.created,
            "previous_created": previous.created,
            "share": round_optional(current.created / total_created, 3) if total_created else None,
            "open": open_count,
            "overdue": overdue,
            "resolution_hours": round_optional(current.resolution_hours, 1),
            "rating": round_optional(current.rating, 2),
            "categories": _category_mix(
                slice_facts,
                start,
                now,
                reaction=reaction,
                resolution=resolution,
            ),
        }
        for address, slice_facts, current, previous, open_count, overdue in listed[:MAX_BUILDINGS]
    ]


def _managers(
    facts: list[TicketFacts],
    dashboard: DashboardResponse,
    start: datetime,
    now: datetime,
    *,
    reaction: timedelta,
    resolution: timedelta,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    by_assignee: dict[int, list[TicketFacts]] = {}
    for fact in facts:
        if fact.assignee_id is None:
            continue
        by_assignee.setdefault(fact.assignee_id, []).append(fact)

    groups: list[tuple[int, WindowMetrics, int, int]] = []
    for assignee_id, slice_facts in by_assignee.items():
        current = window_metrics(
            slice_facts,
            start,
            now,
            previous=False,
            now=now,
            reaction=reaction,
            resolution=resolution,
        )
        open_count = sum(1 for fact in slice_facts if fact.status in OPEN_STATUSES)
        overdue = sum(
            1
            for fact in slice_facts
            if is_overdue(fact, now=now, reaction=reaction, resolution=resolution)
        )
        if current.created == 0 and open_count == 0:
            continue
        groups.append((assignee_id, current, open_count, overdue))

    groups.sort(key=lambda group: (-group[1].created, group[0]))
    groups = groups[:MAX_MANAGERS]

    team_reaction = dashboard.summary.reaction_minutes.value
    team_resolution = dashboard.summary.resolution_hours.value

    managers: list[dict[str, Any]] = []
    manager_refs: dict[str, int] = {}
    for index, (assignee_id, current, open_count, overdue) in enumerate(groups, start=1):
        ref = f"m{index}"
        manager_refs[ref] = assignee_id
        reaction_minutes = round_optional(current.reaction_minutes, 1)
        resolution_hours = round_optional(current.resolution_hours, 1)
        managers.append(
            {
                "ref": ref,
                "assigned": current.created,
                "reaction_minutes": reaction_minutes,
                "reaction_on_time": round_optional(current.reaction_on_time, 3),
                "resolution_hours": resolution_hours,
                "resolution_on_time": round_optional(current.resolution_on_time, 3),
                "rating": round_optional(current.rating, 2),
                "rating_count": current.rating_count,
                "open": open_count,
                "overdue": overdue,
                "reaction_vs_team": _ratio(reaction_minutes, team_reaction),
                "resolution_vs_team": _ratio(resolution_hours, team_resolution),
            }
        )
    return managers, manager_refs


def _category_mix(
    facts: list[TicketFacts],
    start: datetime,
    now: datetime,
    *,
    reaction: timedelta,
    resolution: timedelta,
) -> dict[str, int]:
    by_category: dict[int, list[TicketFacts]] = {}
    for fact in facts:
        if fact.type != TicketType.REQUEST or fact.category_id is None:
            continue
        by_category.setdefault(fact.category_id, []).append(fact)

    counts: list[tuple[str, int]] = []
    for slice_facts in by_category.values():
        created = window_metrics(
            slice_facts,
            start,
            now,
            previous=False,
            now=now,
            reaction=reaction,
            resolution=resolution,
        ).created
        if created == 0:
            continue
        counts.append((_title(slice_facts), created))

    counts.sort(key=lambda item: (-item[1], item[0]))
    return {title: count for title, count in counts}


def _title(facts: list[TicketFacts]) -> str:
    return next((fact.category_title for fact in facts if fact.category_title is not None), "")


def _ratio(value: float | None, team: float | None) -> float | None:
    if value is None or team is None or team == 0:
        return None
    return round_optional(value / team, 1)
