import json
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from src.core.constants import TicketStatus, TicketType
from src.services.dashboard import TicketFacts, build_dashboard
from src.services.insight_payload import build_insight_payload

TZ = ZoneInfo("Europe/Moscow")
NOW = datetime(2026, 9, 29, 9, 0, tzinfo=UTC)  # 12:00 Moscow
REACTION = timedelta(hours=4)
RESOLUTION = timedelta(hours=72)


def fact(
    *,
    created_at: datetime,
    type: TicketType = TicketType.REQUEST,
    status: TicketStatus = TicketStatus.NEW,
    category_id: int | None = 1,
    category_title: str | None = "🚰 Сантехника",
    category_sort_order: int | None = 1,
    closed_at: datetime | None = None,
    reacted_at: datetime | None = None,
    rating: int | None = None,
    building_id: int | None = None,
    building_address: str | None = None,
    assignee_id: int | None = None,
) -> TicketFacts:
    return TicketFacts(
        type=type,
        status=status,
        category_id=category_id,
        category_title=category_title,
        category_sort_order=category_sort_order,
        created_at=created_at,
        closed_at=closed_at,
        reacted_at=reacted_at,
        rating=rating,
        building_id=building_id,
        building_address=building_address,
        assignee_id=assignee_id,
    )


def _ago(**kwargs) -> datetime:
    return NOW - timedelta(**kwargs)


def run(facts: list[TicketFacts], *, days: int = 30):
    dashboard = build_dashboard(
        facts,
        now=NOW,
        days=days,
        tz=TZ,
        reaction=REACTION,
        resolution=RESOLUTION,
    )
    return build_insight_payload(
        facts,
        dashboard,
        now=NOW,
        days=days,
        tz=TZ,
        reaction=REACTION,
        resolution=RESOLUTION,
    )


def test_shape_and_copied_blocks() -> None:
    facts = [
        fact(created_at=_ago(days=2)),
        fact(created_at=_ago(days=40), category_id=2, category_title="🛗 Лифт"),
    ]

    payload = run(facts)
    dashboard = build_dashboard(
        facts, now=NOW, days=30, tz=TZ, reaction=REACTION, resolution=RESOLUTION
    )
    dumped = dashboard.model_dump(mode="json")

    assert set(payload.data) == {
        "period_days",
        "sla",
        "now",
        "summary",
        "daily",
        "questions",
        "categories",
        "buildings",
        "managers",
    }
    for key in ("period_days", "sla", "now", "summary", "daily", "questions"):
        assert payload.data[key] == dumped[key]
    json.dumps(payload.data)


def test_empty_facts() -> None:
    payload = run([])

    assert payload.data["categories"] == []
    assert payload.data["buildings"] == []
    assert payload.data["managers"] == []
    assert payload.manager_refs == {}
    json.dumps(payload.data)


def test_categories_count_current_and_previous() -> None:
    facts = [
        fact(created_at=_ago(days=2), category_id=1, category_title="🔥 Отопление"),
        fact(created_at=_ago(days=3), category_id=1, category_title="🔥 Отопление"),
        fact(created_at=_ago(days=40), category_id=1, category_title="🔥 Отопление"),
        fact(created_at=_ago(days=2), category_id=2, category_title="🛗 Лифт"),
    ]

    payload = run(facts)
    categories = {category["title"]: category for category in payload.data["categories"]}

    assert categories["🔥 Отопление"]["created"] == 2
    assert categories["🔥 Отопление"]["previous_created"] == 1
    assert categories["🔥 Отопление"]["growth"] == 2.0
    assert categories["🛗 Лифт"]["created"] == 1
    assert categories["🛗 Лифт"]["previous_created"] == 0
    assert categories["🛗 Лифт"]["growth"] is None


def test_category_only_in_previous_window_is_listed_with_zero_growth() -> None:
    facts = [fact(created_at=_ago(days=40), category_id=1, category_title="🔥 Отопление")]

    payload = run(facts)

    assert payload.data["categories"] == [
        {
            "title": "🔥 Отопление",
            "created": 0,
            "previous_created": 1,
            "share": None,
            "growth": 0.0,
            "resolution_hours": None,
            "top_building": None,
        }
    ]


def test_category_shares_sum_to_one() -> None:
    facts = [
        fact(created_at=_ago(days=2), category_id=1, category_title="А"),
        fact(created_at=_ago(days=2), category_id=1, category_title="А"),
        fact(created_at=_ago(days=2), category_id=2, category_title="Б"),
        fact(created_at=_ago(days=2), category_id=3, category_title="В"),
    ]

    payload = run(facts)
    shares = [category["share"] for category in payload.data["categories"]]

    assert sum(shares) == pytest.approx(1, abs=0.01)


def test_categories_order_by_created_then_previous_then_title() -> None:
    facts = [
        # Б: current 2, previous 1.
        fact(created_at=_ago(days=2), category_id=2, category_title="Б"),
        fact(created_at=_ago(days=3), category_id=2, category_title="Б"),
        fact(created_at=_ago(days=40), category_id=2, category_title="Б"),
        # А: current 2, previous 0.
        fact(created_at=_ago(days=2), category_id=1, category_title="А"),
        fact(created_at=_ago(days=3), category_id=1, category_title="А"),
        # В and Г: current 1, previous 5 each; tie broken by title.
        fact(created_at=_ago(days=2), category_id=3, category_title="В"),
        fact(created_at=_ago(days=40), category_id=3, category_title="В"),
        fact(created_at=_ago(days=41), category_id=3, category_title="В"),
        fact(created_at=_ago(days=42), category_id=3, category_title="В"),
        fact(created_at=_ago(days=43), category_id=3, category_title="В"),
        fact(created_at=_ago(days=44), category_id=3, category_title="В"),
        fact(created_at=_ago(days=2), category_id=4, category_title="Г"),
        fact(created_at=_ago(days=40), category_id=4, category_title="Г"),
        fact(created_at=_ago(days=41), category_id=4, category_title="Г"),
        fact(created_at=_ago(days=42), category_id=4, category_title="Г"),
        fact(created_at=_ago(days=43), category_id=4, category_title="Г"),
        fact(created_at=_ago(days=44), category_id=4, category_title="Г"),
    ]

    payload = run(facts)

    assert [category["title"] for category in payload.data["categories"]] == [
        "Б",
        "А",
        "В",
        "Г",
    ]


def test_categories_ignore_questions_and_requests_without_category() -> None:
    facts = [
        fact(
            created_at=_ago(days=2),
            type=TicketType.QUESTION,
            category_id=None,
            category_title=None,
        ),
        fact(created_at=_ago(days=2), category_id=None, category_title=None),
        fact(created_at=_ago(days=2), category_id=1, category_title="А"),
    ]

    payload = run(facts)

    assert [category["title"] for category in payload.data["categories"]] == ["А"]


def test_category_resolution_hours() -> None:
    facts = [
        fact(
            created_at=_ago(days=10),
            category_id=1,
            category_title="А",
            status=TicketStatus.CLOSED,
            closed_at=_ago(days=9),  # 24h
        ),
        fact(
            created_at=_ago(days=10),
            category_id=1,
            category_title="А",
            status=TicketStatus.CLOSED,
            closed_at=_ago(days=8),  # 48h
        ),
        fact(created_at=_ago(days=2), category_id=2, category_title="Б"),
    ]

    payload = run(facts)
    categories = {category["title"]: category for category in payload.data["categories"]}

    assert categories["А"]["resolution_hours"] == 36.0
    assert categories["Б"]["resolution_hours"] is None


def test_category_top_building() -> None:
    facts = [
        fact(
            created_at=_ago(days=2),
            category_id=1,
            category_title="🛗 Лифт",
            building_id=2,
            building_address="ул. Мира, 2",
        ),
        fact(
            created_at=_ago(days=3),
            category_id=1,
            category_title="🛗 Лифт",
            building_id=2,
            building_address="ул. Мира, 2",
        ),
        fact(
            created_at=_ago(days=4),
            category_id=1,
            category_title="🛗 Лифт",
            building_id=2,
            building_address="ул. Мира, 2",
        ),
        fact(
            created_at=_ago(days=2),
            category_id=1,
            category_title="🛗 Лифт",
            building_id=1,
            building_address="ул. Ленина, 1",
        ),
    ]

    payload = run(facts)
    category = payload.data["categories"][0]

    assert category["created"] == 4
    assert category["top_building"] == {
        "address": "ул. Мира, 2",
        "created": 3,
        "share": 0.75,
    }


def test_category_top_building_tie_broken_by_address() -> None:
    facts = [
        fact(
            created_at=_ago(days=2),
            category_id=1,
            category_title="Лифт",
            building_id=1,
            building_address="Б",
        ),
        fact(
            created_at=_ago(days=2),
            category_id=1,
            category_title="Лифт",
            building_id=2,
            building_address="А",
        ),
    ]

    payload = run(facts)
    category = payload.data["categories"][0]

    assert category["top_building"] == {"address": "А", "created": 1, "share": 0.5}


def test_category_top_building_is_none_without_buildings() -> None:
    facts = [fact(created_at=_ago(days=2), category_id=1, category_title="Лифт")]

    payload = run(facts)

    assert payload.data["categories"][0]["top_building"] is None


def test_category_top_building_ignores_previous_window() -> None:
    facts = [
        fact(
            created_at=_ago(days=2),
            category_id=1,
            category_title="Лифт",
            building_id=1,
            building_address="Старый",
        ),
        fact(
            created_at=_ago(days=40),
            category_id=1,
            category_title="Лифт",
            building_id=2,
            building_address="Новый",
        ),
        fact(
            created_at=_ago(days=41),
            category_id=1,
            category_title="Лифт",
            building_id=2,
            building_address="Новый",
        ),
        fact(
            created_at=_ago(days=42),
            category_id=1,
            category_title="Лифт",
            building_id=2,
            building_address="Новый",
        ),
    ]

    payload = run(facts)
    category = payload.data["categories"][0]

    assert category["top_building"] == {"address": "Старый", "created": 1, "share": 1.0}


def test_category_top_building_ignores_tickets_without_address() -> None:
    facts = [
        fact(
            created_at=_ago(days=2),
            category_id=1,
            category_title="Лифт",
            building_id=1,
            building_address=None,
        ),
        fact(
            created_at=_ago(days=2),
            category_id=1,
            category_title="Лифт",
            building_id=2,
            building_address="ул. Мира, 2",
        ),
    ]

    payload = run(facts)
    category = payload.data["categories"][0]

    assert category["top_building"] == {
        "address": "ул. Мира, 2",
        "created": 1,
        "share": 0.5,
    }


def test_buildings_numbers() -> None:
    facts = [
        fact(
            created_at=_ago(days=2),
            building_id=1,
            building_address="ул. Ленина, 1",
            status=TicketStatus.IN_PROGRESS,
        ),
        fact(
            created_at=_ago(days=3),
            building_id=1,
            building_address="ул. Ленина, 1",
            status=TicketStatus.IN_PROGRESS,
        ),
        fact(
            created_at=_ago(hours=80),
            building_id=1,
            building_address="ул. Ленина, 1",
            status=TicketStatus.IN_PROGRESS,
        ),
        fact(
            created_at=_ago(days=10),
            building_id=1,
            building_address="ул. Ленина, 1",
            status=TicketStatus.CLOSED,
            closed_at=_ago(days=9),
            rating=5,
        ),
        fact(
            created_at=_ago(days=40),
            building_id=1,
            building_address="ул. Ленина, 1",
            status=TicketStatus.CLOSED,
            closed_at=_ago(days=39),
        ),
        fact(created_at=_ago(hours=1), building_id=2, building_address="ул. Мира, 2"),
    ]

    payload = run(facts)
    buildings = {building["address"]: building for building in payload.data["buildings"]}

    first = buildings["ул. Ленина, 1"]
    assert first["created"] == 4
    assert first["previous_created"] == 1
    assert first["share"] == 0.8
    assert first["open"] == 3
    assert first["overdue"] == 1
    assert first["resolution_hours"] == 24.0
    assert first["rating"] == 5.0

    second = buildings["ул. Мира, 2"]
    assert second["created"] == 1
    assert second["share"] == 0.2
    assert second["open"] == 1
    assert second["overdue"] == 0
    assert second["resolution_hours"] is None
    assert second["rating"] is None

    assert [building["address"] for building in payload.data["buildings"]] == [
        "ул. Ленина, 1",
        "ул. Мира, 2",
    ]


def test_building_category_mix() -> None:
    facts = [
        fact(
            created_at=_ago(days=2),
            building_id=1,
            building_address="A",
            category_id=1,
            category_title="Лифт",
        ),
        fact(
            created_at=_ago(days=2),
            building_id=1,
            building_address="A",
            category_id=1,
            category_title="Лифт",
        ),
        fact(
            created_at=_ago(days=2),
            building_id=1,
            building_address="A",
            category_id=2,
            category_title="Сантехника",
        ),
        fact(
            created_at=_ago(days=40),
            building_id=1,
            building_address="A",
            category_id=3,
            category_title="Электрика",
        ),
        fact(
            created_at=_ago(days=2),
            building_id=1,
            building_address="A",
            type=TicketType.QUESTION,
            category_id=None,
            category_title=None,
        ),
    ]

    payload = run(facts)

    assert payload.data["buildings"][0]["categories"] == {"Лифт": 2, "Сантехника": 1}


def test_building_ignores_tickets_without_building() -> None:
    payload = run([fact(created_at=_ago(days=2), building_id=None)])

    assert payload.data["buildings"] == []


def test_building_without_address_is_skipped_and_not_in_share() -> None:
    facts = [
        fact(created_at=_ago(days=2), building_id=1, building_address=None),
        fact(created_at=_ago(days=2), building_id=2, building_address="ул. Мира, 2"),
    ]

    payload = run(facts)

    assert [building["address"] for building in payload.data["buildings"]] == ["ул. Мира, 2"]
    assert payload.data["buildings"][0]["share"] == 1.0


def test_building_with_only_old_closed_is_not_listed() -> None:
    facts = [
        fact(
            created_at=_ago(days=70),
            building_id=1,
            building_address="A",
            status=TicketStatus.CLOSED,
            closed_at=_ago(days=69),
        )
    ]

    payload = run(facts)

    assert payload.data["buildings"] == []


def test_building_with_old_open_is_listed() -> None:
    facts = [
        fact(
            created_at=_ago(days=70),
            building_id=1,
            building_address="A",
            status=TicketStatus.IN_PROGRESS,
        )
    ]

    payload = run(facts)

    assert [building["address"] for building in payload.data["buildings"]] == ["A"]
    assert payload.data["buildings"][0]["created"] == 0
    assert payload.data["buildings"][0]["open"] == 1


def test_buildings_cap_keeps_biggest() -> None:
    facts = []
    for index in range(1, 13):
        for _ in range(index):
            facts.append(
                fact(
                    created_at=_ago(days=2),
                    building_id=index,
                    building_address=f"Дом {index:02d}",
                )
            )

    payload = run(facts)

    assert len(payload.data["buildings"]) == 10
    assert [building["address"] for building in payload.data["buildings"]] == [
        f"Дом {index:02d}" for index in range(12, 2, -1)
    ]


def test_managers_labels_and_refs_follow_sort() -> None:
    facts = [
        fact(created_at=_ago(days=2), assignee_id=101),
        fact(created_at=_ago(days=3), assignee_id=101),
        fact(created_at=_ago(days=2), assignee_id=102),
        fact(created_at=_ago(days=2), assignee_id=None),
    ]

    payload = run(facts)
    managers = payload.data["managers"]

    assert [manager["ref"] for manager in managers] == ["m1", "m2"]
    assert [manager["assigned"] for manager in managers] == [2, 1]
    assert payload.manager_refs == {"m1": 101, "m2": 102}


def test_manager_open_and_overdue() -> None:
    facts = [
        fact(created_at=_ago(hours=1), assignee_id=101),
        fact(
            created_at=_ago(hours=80),
            assignee_id=101,
            status=TicketStatus.IN_PROGRESS,
        ),
        fact(
            created_at=_ago(days=10),
            assignee_id=101,
            status=TicketStatus.CLOSED,
            closed_at=_ago(days=9),
        ),
    ]

    payload = run(facts)
    manager = payload.data["managers"][0]

    assert manager["assigned"] == 3
    assert manager["open"] == 2
    assert manager["overdue"] == 1


def test_managers_reaction_vs_others() -> None:
    created = _ago(days=2)
    facts = [
        fact(created_at=created, assignee_id=101, reacted_at=created + timedelta(minutes=180)),
        fact(created_at=created, assignee_id=102, reacted_at=created + timedelta(minutes=60)),
    ]

    payload = run(facts)
    managers = {manager["ref"]: manager for manager in payload.data["managers"]}

    assert managers["m1"]["reaction_minutes"] == 180.0
    assert managers["m1"]["reaction_vs_others"] == 3.0
    assert managers["m2"]["reaction_minutes"] == 60.0
    assert managers["m2"]["reaction_vs_others"] == 0.3


def test_managers_vs_others_is_none_with_single_manager() -> None:
    created = _ago(days=2)
    facts = [
        fact(created_at=created, assignee_id=101, reacted_at=created + timedelta(minutes=180)),
    ]

    payload = run(facts)
    manager = payload.data["managers"][0]

    assert manager["reaction_vs_others"] is None
    assert manager["resolution_vs_others"] is None


def test_managers_vs_others_ignores_unassigned_tickets() -> None:
    created = _ago(days=2)
    facts = [
        fact(created_at=created, assignee_id=101, reacted_at=created + timedelta(minutes=180)),
        fact(created_at=created, assignee_id=102),
        fact(created_at=created, assignee_id=None, reacted_at=created + timedelta(minutes=60)),
        fact(created_at=created, assignee_id=None, reacted_at=created + timedelta(minutes=60)),
    ]

    payload = run(facts)
    managers = {manager["ref"]: manager for manager in payload.data["managers"]}

    # The only other assigned ticket has no reaction, so there is nothing to compare to.
    assert managers["m1"]["reaction_vs_others"] is None


def test_managers_vs_others_is_none_without_others_reaction() -> None:
    created = _ago(days=2)
    facts = [
        fact(created_at=created, assignee_id=101, reacted_at=created + timedelta(minutes=180)),
        fact(created_at=created, assignee_id=102),
    ]

    payload = run(facts)
    managers = {manager["ref"]: manager for manager in payload.data["managers"]}

    assert managers["m1"]["reaction_vs_others"] is None


def test_managers_resolution_vs_others() -> None:
    created = _ago(days=10)
    facts = [
        fact(
            created_at=created,
            assignee_id=101,
            status=TicketStatus.CLOSED,
            closed_at=created + timedelta(hours=180),
        ),
        fact(
            created_at=created,
            assignee_id=102,
            status=TicketStatus.CLOSED,
            closed_at=created + timedelta(hours=60),
        ),
    ]

    payload = run(facts)
    managers = {manager["ref"]: manager for manager in payload.data["managers"]}

    assert managers["m1"]["resolution_hours"] == 180.0
    assert managers["m1"]["resolution_vs_others"] == 3.0
    assert managers["m2"]["resolution_hours"] == 60.0
    assert managers["m2"]["resolution_vs_others"] == 0.3


def test_manager_outside_top_ten_counts_in_others() -> None:
    created = _ago(days=2)
    facts = [
        fact(created_at=created, assignee_id=101, reacted_at=created + timedelta(minutes=180)),
    ]
    for assignee_id in range(102, 111):
        facts.append(
            fact(
                created_at=created,
                assignee_id=assignee_id,
                reacted_at=created + timedelta(minutes=60),
            )
        )
    # The 11th manager is cut from the report but still counted among "others".
    facts.append(fact(created_at=created, assignee_id=111, reacted_at=created))

    payload = run(facts)
    managers = {manager["ref"]: manager for manager in payload.data["managers"]}

    assert "m11" not in managers
    # Others = nine tickets at 60 min plus one at 0 min -> mean 54 min.
    assert managers["m1"]["reaction_vs_others"] == 3.3


def test_managers_cap_keeps_biggest() -> None:
    facts = []
    for index in range(1, 13):
        for _ in range(index):
            facts.append(fact(created_at=_ago(days=2), assignee_id=100 + index))

    payload = run(facts)
    managers = payload.data["managers"]

    assert len(managers) == 10
    assert [manager["assigned"] for manager in managers] == [12, 11, 10, 9, 8, 7, 6, 5, 4, 3]
    assert payload.manager_refs == {f"m{index}": 113 - index for index in range(1, 11)}


def test_privacy_no_assignee_ids_in_data() -> None:
    facts = [
        fact(created_at=_ago(days=2), assignee_id=424242),
        fact(created_at=_ago(days=2), assignee_id=424242),
    ]

    payload = run(facts)
    text = json.dumps(payload.data)

    assert "424242" not in text
    assert "assignee_id" not in text
    assert payload.manager_refs == {"m1": 424242}


def test_demo_patterns_scenario() -> None:
    facts: list[TicketFacts] = []

    # Pattern 1: heating jumped 3x in the current window.
    for _ in range(9):
        facts.append(fact(created_at=_ago(days=2), category_id=10, category_title="🔥 Отопление"))
    for _ in range(3):
        facts.append(fact(created_at=_ago(days=40), category_id=10, category_title="🔥 Отопление"))

    # Pattern 2: one building has most of the lift requests.
    for _ in range(6):
        facts.append(
            fact(
                created_at=_ago(days=2),
                building_id=1,
                building_address="ул. Лифтовая, 1",
                category_id=20,
                category_title="🛗 Лифт",
            )
        )
    for _ in range(2):
        facts.append(
            fact(
                created_at=_ago(days=2),
                building_id=2,
                building_address="ул. Мира, 2",
                category_id=20,
                category_title="🛗 Лифт",
            )
        )

    # Pattern 3: one manager reacts three times slower than the team.
    created = _ago(days=2)
    facts.append(
        fact(
            created_at=created,
            assignee_id=201,
            category_id=None,
            category_title=None,
            reacted_at=created + timedelta(minutes=180),
        )
    )
    facts.append(
        fact(
            created_at=created,
            assignee_id=202,
            category_id=None,
            category_title=None,
            reacted_at=created + timedelta(minutes=60),
        )
    )
    facts.append(
        fact(
            created_at=created,
            assignee_id=203,
            category_id=None,
            category_title=None,
            reacted_at=created + timedelta(minutes=60),
        )
    )
    facts.append(
        fact(
            created_at=created,
            assignee_id=None,
            category_id=None,
            category_title=None,
            reacted_at=created,
        )
    )
    facts.append(
        fact(
            created_at=created,
            assignee_id=None,
            category_id=None,
            category_title=None,
            reacted_at=created,
        )
    )

    payload = run(facts)
    data = payload.data

    heating = next(
        category for category in data["categories"] if category["title"] == "🔥 Отопление"
    )
    assert heating["created"] == 9
    assert heating["previous_created"] == 3
    assert heating["growth"] == 3.0

    lift_building = next(
        building for building in data["buildings"] if building["address"] == "ул. Лифтовая, 1"
    )
    assert lift_building["categories"]["🛗 Лифт"] == 6

    lift_category = next(
        category for category in data["categories"] if category["title"] == "🛗 Лифт"
    )
    assert lift_category["top_building"] == {
        "address": "ул. Лифтовая, 1",
        "created": 6,
        "share": 0.75,
    }

    slow = next(manager for manager in data["managers"] if manager["ref"] == "m1")
    assert slow["reaction_vs_others"] == 3.0
