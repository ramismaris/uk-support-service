from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from src.core.constants import TicketStatus, TicketType
from src.services.dashboard import TicketFacts, build_dashboard

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
    )


def run(facts: list[TicketFacts], *, days: int = 30):
    return build_dashboard(
        facts,
        now=NOW,
        days=days,
        tz=TZ,
        reaction=REACTION,
        resolution=RESOLUTION,
    )


def _ago(**kwargs) -> datetime:
    return NOW - timedelta(**kwargs)


def test_bounds_for_7_and_30_days() -> None:
    response = run([], days=7)

    assert response.period_days == 7
    assert response.date_from == date(2026, 9, 23)
    assert response.date_to == date(2026, 9, 29)
    assert len(response.daily) == 7
    assert [day.date for day in response.daily] == [
        date(2026, 9, 23) + timedelta(days=offset) for offset in range(7)
    ]

    long_response = run([], days=30)

    assert long_response.period_days == 30
    assert long_response.date_from == date(2026, 8, 31)
    assert long_response.date_to == date(2026, 9, 29)
    assert len(long_response.daily) == 30


def test_daily_uses_moscow_days_and_windows() -> None:
    late_evening = fact(
        created_at=datetime(2026, 9, 28, 20, 30, tzinfo=UTC)  # 23:30 MSK on 2026-09-28
    )
    just_after_midnight = fact(
        created_at=datetime(2026, 9, 22, 21, 10, tzinfo=UTC)  # 00:10 MSK on 2026-09-23
    )
    before_window = fact(
        created_at=datetime(2026, 9, 22, 20, 50, tzinfo=UTC)  # 23:50 MSK on 2026-09-22
    )

    response = run([late_evening, just_after_midnight, before_window], days=7)

    assert response.summary.created.value == 2
    assert response.summary.created.previous == 1
    by_date = {day.date: day for day in response.daily}
    assert by_date[date(2026, 9, 28)].created == 1
    assert by_date[date(2026, 9, 23)].created == 1
    assert date(2026, 9, 22) not in by_date


def test_now_counts_by_status_and_overdue() -> None:
    facts = [
        fact(created_at=_ago(hours=5), status=TicketStatus.NEW),  # overdue
        fact(created_at=_ago(hours=3), status=TicketStatus.NEW),  # has time
        fact(created_at=_ago(hours=80), status=TicketStatus.IN_PROGRESS),  # overdue
        fact(created_at=_ago(hours=71), status=TicketStatus.WAITING_CLIENT),  # has time
        fact(created_at=_ago(hours=80), status=TicketStatus.NEW),  # overdue, counted once
        fact(
            created_at=_ago(hours=200),
            status=TicketStatus.CLOSED,
            closed_at=_ago(hours=100),
        ),  # never overdue
    ]

    response = run(facts)

    assert response.now.new == 3
    assert response.now.in_progress == 1
    assert response.now.waiting_client == 1
    assert response.now.overdue == 3


def test_now_overdue_boundary_is_strict() -> None:
    facts = [
        fact(created_at=_ago(hours=4), status=TicketStatus.NEW),  # exactly 4h - not overdue
        fact(created_at=_ago(hours=72), status=TicketStatus.IN_PROGRESS),  # exactly 72h - no
    ]

    response = run(facts)

    assert response.now.overdue == 0


def test_created_and_closed_with_previous() -> None:
    current = fact(created_at=datetime(2026, 9, 10, 9, 0, tzinfo=UTC))
    previous = fact(created_at=datetime(2026, 8, 10, 9, 0, tzinfo=UTC))
    closed_in_window = fact(
        created_at=datetime(2026, 9, 1, 9, 0, tzinfo=UTC),
        status=TicketStatus.CLOSED,
        closed_at=datetime(2026, 9, 5, 9, 0, tzinfo=UTC),
    )
    rejected_in_window = fact(
        created_at=datetime(2026, 9, 1, 9, 0, tzinfo=UTC),
        status=TicketStatus.REJECTED,
        closed_at=datetime(2026, 9, 5, 9, 0, tzinfo=UTC),
    )

    response = run([current, previous, closed_in_window, rejected_in_window])

    # current, closed_in_window and rejected_in_window were created in the window;
    # rejected is not closed.
    assert response.summary.created.value == 3
    assert response.summary.created.previous == 1
    assert response.summary.closed.value == 1
    assert response.summary.closed.previous == 0


def test_reaction_minutes_means_created_in_window_and_ignores_missing() -> None:
    facts = [
        fact(created_at=_ago(hours=10), reacted_at=_ago(hours=9)),  # 60 min
        fact(created_at=_ago(hours=10), reacted_at=_ago(hours=8)),  # 120 min
        fact(created_at=_ago(hours=5)),  # no reaction, ignored
    ]

    response = run(facts)

    assert response.summary.reaction_minutes.value == 90.0
    assert response.summary.reaction_minutes.previous is None


def test_reaction_minutes_is_none_without_reactions() -> None:
    response = run([fact(created_at=_ago(hours=5)), fact(created_at=_ago(hours=6))])

    assert response.summary.reaction_minutes.value is None


def test_reaction_on_time_boundary_and_skipped() -> None:
    facts = [
        fact(created_at=_ago(hours=10), reacted_at=_ago(hours=6)),  # exactly 4h - on time
        fact(
            created_at=_ago(hours=10),
            reacted_at=_ago(hours=6) + timedelta(minutes=1),  # 4h 1min - late
        ),
        fact(created_at=_ago(hours=5)),  # no reaction, 5h old - late
        fact(created_at=_ago(hours=1)),  # no reaction, 1h old - skipped
    ]

    response = run(facts)

    assert response.summary.reaction_on_time.value == 0.333


def test_reaction_on_time_is_none_when_only_skipped() -> None:
    response = run([fact(created_at=_ago(hours=1))])

    assert response.summary.reaction_on_time.value is None


def test_resolution_hours_and_on_time() -> None:
    facts = [
        fact(
            created_at=_ago(hours=100),
            status=TicketStatus.CLOSED,
            closed_at=_ago(hours=28),  # 72h - on time
        ),
        fact(
            created_at=_ago(hours=200),
            status=TicketStatus.CLOSED,
            closed_at=_ago(hours=127),  # 73h - late
        ),
    ]

    response = run(facts)

    assert response.summary.resolution_hours.value == 72.5
    assert response.summary.resolution_on_time.value == 0.5


def test_resolution_is_none_without_closed_in_window() -> None:
    response = run([fact(created_at=_ago(hours=5))])

    assert response.summary.resolution_hours.value is None
    assert response.summary.resolution_on_time.value is None


def test_rating_mean_count_and_previous() -> None:
    facts = [
        fact(
            created_at=_ago(hours=100),
            status=TicketStatus.CLOSED,
            closed_at=_ago(hours=30),
            rating=5,
        ),
        fact(
            created_at=_ago(hours=100),
            status=TicketStatus.CLOSED,
            closed_at=_ago(hours=30),
            rating=3,
        ),
        fact(created_at=_ago(hours=100), status=TicketStatus.CLOSED, closed_at=_ago(hours=30)),
        fact(
            created_at=datetime(2026, 8, 10, 9, 0, tzinfo=UTC),
            status=TicketStatus.CLOSED,
            closed_at=datetime(2026, 8, 15, 9, 0, tzinfo=UTC),
            rating=2,
        ),
    ]

    response = run(facts)

    assert response.summary.rating.value == 4.0
    assert response.summary.rating.count == 2
    assert response.summary.rating.previous == 2.0


def test_rating_is_none_without_ratings() -> None:
    response = run([fact(created_at=_ago(hours=1))])

    assert response.summary.rating.value is None
    assert response.summary.rating.previous is None
    assert response.summary.rating.count == 0


def test_daily_sums_match_summary() -> None:
    facts = [
        fact(created_at=_ago(hours=1)),
        fact(created_at=_ago(days=5)),
        fact(
            created_at=_ago(hours=100),
            status=TicketStatus.CLOSED,
            closed_at=_ago(hours=30),
        ),
        fact(
            created_at=_ago(days=10),
            status=TicketStatus.CLOSED,
            closed_at=_ago(days=2),
        ),
        fact(created_at=datetime(2026, 8, 10, 9, 0, tzinfo=UTC)),
    ]

    response = run(facts)

    assert sum(day.created for day in response.daily) == response.summary.created.value
    assert sum(day.closed for day in response.daily) == response.summary.closed.value


def test_categories_group_requests_and_keep_zero_created() -> None:
    facts = [
        fact(
            created_at=datetime(2026, 9, 10, 9, 0, tzinfo=UTC),
            category_id=1,
            category_title="🚰 Сантехника",
        ),
        fact(
            created_at=datetime(2026, 9, 11, 9, 0, tzinfo=UTC),
            category_id=1,
            category_title="🚰 Сантехника",
        ),
        fact(
            created_at=datetime(2026, 9, 1, 9, 0, tzinfo=UTC),
            category_id=1,
            category_title="🚰 Сантехника",
            status=TicketStatus.CLOSED,
            closed_at=datetime(2026, 9, 5, 9, 0, tzinfo=UTC),
        ),
        fact(
            created_at=datetime(2026, 9, 12, 9, 0, tzinfo=UTC),
            category_id=3,
            category_title="🛗 Лифт",
        ),
        fact(
            created_at=datetime(2026, 8, 1, 9, 0, tzinfo=UTC),
            category_id=2,
            category_title="⚡️ Электрика",
            status=TicketStatus.CLOSED,
            closed_at=datetime(2026, 9, 3, 9, 0, tzinfo=UTC),
        ),
        fact(
            created_at=datetime(2026, 9, 10, 9, 0, tzinfo=UTC),
            type=TicketType.QUESTION,
            category_id=None,
            category_title=None,
        ),
        fact(
            created_at=datetime(2026, 9, 1, 9, 0, tzinfo=UTC),
            type=TicketType.QUESTION,
            category_id=None,
            category_title=None,
            status=TicketStatus.CLOSED,
            closed_at=datetime(2026, 9, 4, 9, 0, tzinfo=UTC),
        ),
    ]

    response = run(facts)

    assert [(category.category_id, category.created) for category in response.categories] == [
        (1, 3),
        (3, 1),
        (2, 0),
    ]
    assert [category.title for category in response.categories] == [
        "🚰 Сантехника",
        "🛗 Лифт",
        "⚡️ Электрика",
    ]
    assert response.categories[0].resolution_hours == 96.0
    assert response.categories[1].resolution_hours is None
    assert response.categories[2].resolution_hours == 792.0
    assert response.questions.created == 2
    assert response.questions.resolution_hours == 72.0


def test_categories_sorted_by_created_then_category_order_then_title() -> None:
    def request(category_id: int, title: str, order: int, days: int) -> TicketFacts:
        return fact(
            created_at=_ago(days=days),
            category_id=category_id,
            category_title=title,
            category_sort_order=order,
        )

    facts = [
        request(10, "🚰 Сантехника", 1, 2),
        request(11, "⚡️ Электрика", 2, 2),
        request(12, "🔥 Отопление", 4, 2),
        request(13, "🛗 Лифт", 3, 3),
        request(13, "🛗 Лифт", 3, 3),
        request(14, "Б", 5, 2),
        request(15, "А", 5, 2),
    ]

    response = run(facts)

    # By title alone the emoji code points would give ⚡️, 🔥, 🚰.
    assert [category.title for category in response.categories] == [
        "🛗 Лифт",
        "🚰 Сантехника",
        "⚡️ Электрика",
        "🔥 Отопление",
        "А",
        "Б",
    ]


def test_rounds_reaction_minutes_to_one_decimal() -> None:
    response = run(
        [
            fact(
                created_at=_ago(hours=10),
                reacted_at=_ago(hours=10) + timedelta(hours=1, minutes=1, seconds=20),
            )
        ]
    )

    assert response.summary.reaction_minutes.value == 61.3


def test_rounds_resolution_hours_to_one_decimal() -> None:
    response = run(
        [
            fact(
                created_at=_ago(hours=100),
                status=TicketStatus.CLOSED,
                closed_at=_ago(hours=100) + timedelta(hours=72, minutes=20),
            )
        ]
    )

    assert response.summary.resolution_hours.value == 72.3


def test_rounds_shares_to_three_decimals() -> None:
    facts = [
        fact(created_at=_ago(hours=10), reacted_at=_ago(hours=6)),  # 4h - on time
        fact(created_at=_ago(hours=10), reacted_at=_ago(hours=5)),  # 5h - late
        fact(created_at=_ago(hours=5), reacted_at=_ago(hours=4)),  # 1h - on time
    ]
    # Two on time (4h and 1h), one late (5h): 2/3.
    response = run(facts)

    assert response.summary.reaction_on_time.value == 0.667


def test_rounds_rating_to_two_decimals() -> None:
    facts = [
        fact(
            created_at=_ago(hours=100),
            status=TicketStatus.CLOSED,
            closed_at=_ago(hours=30),
            rating=5,
        ),
        fact(
            created_at=_ago(hours=100),
            status=TicketStatus.CLOSED,
            closed_at=_ago(hours=30),
            rating=4,
        ),
        fact(
            created_at=_ago(hours=100),
            status=TicketStatus.CLOSED,
            closed_at=_ago(hours=30),
            rating=4,
        ),
    ]

    response = run(facts)

    assert response.summary.rating.value == 4.33


def test_no_facts_gives_zeros_nones_and_daily_points() -> None:
    response = run([])

    assert response.sla.reaction_hours == 4
    assert response.sla.resolution_hours == 72
    assert response.now.new == 0
    assert response.now.in_progress == 0
    assert response.now.waiting_client == 0
    assert response.now.overdue == 0
    assert response.summary.created.value == 0
    assert response.summary.created.previous == 0
    assert response.summary.closed.value == 0
    assert response.summary.closed.previous == 0
    assert response.summary.reaction_minutes.value is None
    assert response.summary.resolution_hours.value is None
    assert response.summary.reaction_on_time.value is None
    assert response.summary.resolution_on_time.value is None
    assert response.summary.rating.value is None
    assert response.summary.rating.previous is None
    assert response.summary.rating.count == 0
    assert len(response.daily) == 30
    assert all(day.created == 0 and day.closed == 0 for day in response.daily)
    assert response.categories == []
    assert response.questions.created == 0
    assert response.questions.resolution_hours is None
