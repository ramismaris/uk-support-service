from datetime import UTC, datetime, timedelta

import pytest

from src.core.constants import TicketStatus, UserRole
from src.core.exceptions import ConflictException, ForbiddenException
from src.services.ticket_rules import (
    CLIENT_REOPEN_WINDOW,
    OPEN_STATUSES,
    AskWhichTicket,
    OfferNewQuestion,
    ToTicket,
    allowed_statuses,
    can_client_reopen,
    can_rate,
    check_transition,
    is_open,
    is_unread,
    route_client_message,
    status_after_client_message,
    status_after_staff_message,
)

NOW = datetime(2026, 1, 10, 12, 0, tzinfo=UTC)

ALL_STATUSES: tuple[TicketStatus, ...] = tuple(TicketStatus)

# Expected "Переходы" table restricted to rows where «Кто» is a person.
ALLOWED: dict[tuple[TicketStatus, TicketStatus], frozenset[UserRole]] = {
    (TicketStatus.NEW, TicketStatus.IN_PROGRESS): frozenset({UserRole.MANAGER, UserRole.ADMIN}),
    (TicketStatus.NEW, TicketStatus.REJECTED): frozenset({UserRole.MANAGER, UserRole.ADMIN}),
    (TicketStatus.IN_PROGRESS, TicketStatus.REJECTED): frozenset(
        {UserRole.MANAGER, UserRole.ADMIN}
    ),
    (TicketStatus.WAITING_CLIENT, TicketStatus.REJECTED): frozenset(
        {UserRole.MANAGER, UserRole.ADMIN}
    ),
    (TicketStatus.IN_PROGRESS, TicketStatus.WAITING_CLIENT): frozenset(
        {UserRole.MANAGER, UserRole.ADMIN}
    ),
    (TicketStatus.IN_PROGRESS, TicketStatus.CLOSED): frozenset({UserRole.MANAGER, UserRole.ADMIN}),
    (TicketStatus.WAITING_CLIENT, TicketStatus.CLOSED): frozenset(
        {UserRole.MANAGER, UserRole.ADMIN}
    ),
    (TicketStatus.CLOSED, TicketStatus.IN_PROGRESS): frozenset({UserRole.CLIENT, UserRole.ADMIN}),
    (TicketStatus.REJECTED, TicketStatus.IN_PROGRESS): frozenset({UserRole.ADMIN}),
}


def _matrix_cases():
    cases = []
    for current in ALL_STATUSES:
        for target in ALL_STATUSES:
            allowed_roles = ALLOWED.get((current, target), frozenset())
            for role in UserRole:
                cases.append(
                    pytest.param(
                        current,
                        target,
                        role,
                        role in allowed_roles,
                        id=f"{current.value}->{target.value}-{role.value}",
                    )
                )
    return cases


@pytest.mark.parametrize(("current", "target", "role", "allowed"), _matrix_cases())
def test_transition_matrix(
    current: TicketStatus,
    target: TicketStatus,
    role: UserRole,
    allowed: bool,
):
    # closed_at / now are inside the window so the matrix checks the table, not the window.
    closed_at = NOW - timedelta(days=1)

    if allowed:
        assert check_transition(current, target, role, closed_at=closed_at, now=NOW) is None
        return

    if (current, target) not in ALLOWED:
        with pytest.raises(ConflictException) as exc_info:
            check_transition(current, target, role, closed_at=closed_at, now=NOW)
        assert exc_info.value.status_code == 409
        assert exc_info.value.message == "Нельзя перевести обращение в этот статус"
    else:
        with pytest.raises(ForbiddenException) as exc_info:
            check_transition(current, target, role, closed_at=closed_at, now=NOW)
        assert exc_info.value.status_code == 403
        assert exc_info.value.message == "Недостаточно прав для этого действия"


def test_client_reopens_one_minute_after_closing():
    check_transition(
        TicketStatus.CLOSED,
        TicketStatus.IN_PROGRESS,
        UserRole.CLIENT,
        closed_at=NOW - timedelta(minutes=1),
        now=NOW,
    )


def test_client_reopens_exactly_seven_days_after_closing():
    check_transition(
        TicketStatus.CLOSED,
        TicketStatus.IN_PROGRESS,
        UserRole.CLIENT,
        closed_at=NOW - timedelta(days=7),
        now=NOW,
    )


def test_client_reopen_after_window_is_rejected():
    with pytest.raises(ConflictException) as exc_info:
        check_transition(
            TicketStatus.CLOSED,
            TicketStatus.IN_PROGRESS,
            UserRole.CLIENT,
            closed_at=NOW - timedelta(days=7, seconds=1),
            now=NOW,
        )
    assert exc_info.value.status_code == 409
    assert (
        exc_info.value.message == "Прошло больше 7 дней после закрытия — создайте новое обращение"
    )


def test_client_reopen_without_closed_at_is_rejected():
    with pytest.raises(ConflictException) as exc_info:
        check_transition(
            TicketStatus.CLOSED,
            TicketStatus.IN_PROGRESS,
            UserRole.CLIENT,
            closed_at=None,
            now=NOW,
        )
    assert exc_info.value.status_code == 409
    assert exc_info.value.message == (
        "Прошло больше 7 дней после закрытия — создайте новое обращение"
    )


def test_admin_reopens_thirty_days_after_closing():
    check_transition(
        TicketStatus.CLOSED,
        TicketStatus.IN_PROGRESS,
        UserRole.ADMIN,
        closed_at=NOW - timedelta(days=30),
        now=NOW,
    )


@pytest.mark.parametrize(
    ("closed_at", "expected"),
    [
        pytest.param(NOW - timedelta(minutes=1), True, id="one-minute"),
        pytest.param(NOW - timedelta(days=7), True, id="exactly-seven-days"),
        pytest.param(NOW - timedelta(days=7, seconds=1), False, id="seven-days-one-second"),
        pytest.param(None, False, id="no-closed-at"),
    ],
)
def test_can_client_reopen_closed(closed_at: datetime | None, expected: bool):
    assert can_client_reopen(TicketStatus.CLOSED, closed_at, NOW) is expected


def test_can_client_reopen_rejected_with_recent_closed_at():
    assert can_client_reopen(TicketStatus.REJECTED, NOW - timedelta(minutes=1), NOW) is False


@pytest.mark.parametrize(
    "status",
    [
        pytest.param(TicketStatus.NEW, id="new"),
        pytest.param(TicketStatus.IN_PROGRESS, id="in-progress"),
        pytest.param(TicketStatus.WAITING_CLIENT, id="waiting-client"),
    ],
)
def test_can_client_reopen_open_status_with_recent_closed_at(status: TicketStatus):
    assert can_client_reopen(status, NOW - timedelta(minutes=1), NOW) is False


@pytest.mark.parametrize(
    ("current", "expected"),
    [
        pytest.param(
            TicketStatus.NEW,
            [TicketStatus.IN_PROGRESS, TicketStatus.REJECTED],
            id="new",
        ),
        pytest.param(
            TicketStatus.IN_PROGRESS,
            [TicketStatus.WAITING_CLIENT, TicketStatus.CLOSED, TicketStatus.REJECTED],
            id="in-progress",
        ),
        pytest.param(
            TicketStatus.WAITING_CLIENT,
            [TicketStatus.CLOSED, TicketStatus.REJECTED],
            id="waiting-client",
        ),
        pytest.param(TicketStatus.CLOSED, [], id="closed"),
        pytest.param(TicketStatus.REJECTED, [], id="rejected"),
    ],
)
def test_allowed_statuses_manager(current: TicketStatus, expected: list[TicketStatus]):
    assert allowed_statuses(current, UserRole.MANAGER, closed_at=None, now=NOW) == expected


@pytest.mark.parametrize(
    ("current", "closed_at", "expected"),
    [
        pytest.param(
            TicketStatus.NEW,
            None,
            [TicketStatus.IN_PROGRESS, TicketStatus.REJECTED],
            id="new",
        ),
        pytest.param(
            TicketStatus.IN_PROGRESS,
            None,
            [TicketStatus.WAITING_CLIENT, TicketStatus.CLOSED, TicketStatus.REJECTED],
            id="in-progress",
        ),
        pytest.param(
            TicketStatus.WAITING_CLIENT,
            None,
            [TicketStatus.CLOSED, TicketStatus.REJECTED],
            id="waiting-client",
        ),
        pytest.param(
            TicketStatus.CLOSED,
            NOW - timedelta(days=30),
            [TicketStatus.IN_PROGRESS],
            id="closed-old",
        ),
        pytest.param(TicketStatus.REJECTED, None, [TicketStatus.IN_PROGRESS], id="rejected"),
    ],
)
def test_allowed_statuses_admin(
    current: TicketStatus, closed_at: datetime | None, expected: list[TicketStatus]
):
    assert allowed_statuses(current, UserRole.ADMIN, closed_at=closed_at, now=NOW) == expected


@pytest.mark.parametrize(
    ("current", "closed_at", "expected"),
    [
        pytest.param(TicketStatus.NEW, None, [], id="new"),
        pytest.param(TicketStatus.IN_PROGRESS, None, [], id="in-progress"),
        pytest.param(TicketStatus.WAITING_CLIENT, None, [], id="waiting-client"),
        pytest.param(
            TicketStatus.CLOSED,
            NOW - timedelta(days=1),
            [TicketStatus.IN_PROGRESS],
            id="closed-inside-window",
        ),
        pytest.param(
            TicketStatus.CLOSED,
            NOW - timedelta(days=7),
            [TicketStatus.IN_PROGRESS],
            id="closed-exactly-seven-days",
        ),
        pytest.param(TicketStatus.CLOSED, NOW - timedelta(days=8), [], id="closed-outside-window"),
        pytest.param(TicketStatus.CLOSED, None, [], id="closed-without-closed-at"),
        pytest.param(TicketStatus.REJECTED, NOW - timedelta(days=1), [], id="rejected"),
    ],
)
def test_allowed_statuses_client(
    current: TicketStatus, closed_at: datetime | None, expected: list[TicketStatus]
):
    assert allowed_statuses(current, UserRole.CLIENT, closed_at=closed_at, now=NOW) == expected


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        pytest.param(TicketStatus.NEW, TicketStatus.IN_PROGRESS, id="new"),
        pytest.param(TicketStatus.IN_PROGRESS, None, id="in-progress"),
        pytest.param(TicketStatus.WAITING_CLIENT, None, id="waiting-client"),
        pytest.param(TicketStatus.CLOSED, None, id="closed"),
        pytest.param(TicketStatus.REJECTED, None, id="rejected"),
    ],
)
def test_status_after_staff_message(status: TicketStatus, expected: TicketStatus | None):
    assert status_after_staff_message(status) is expected


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        pytest.param(TicketStatus.NEW, None, id="new"),
        pytest.param(TicketStatus.IN_PROGRESS, None, id="in-progress"),
        pytest.param(TicketStatus.WAITING_CLIENT, TicketStatus.IN_PROGRESS, id="waiting-client"),
        pytest.param(TicketStatus.CLOSED, None, id="closed"),
        pytest.param(TicketStatus.REJECTED, None, id="rejected"),
    ],
)
def test_status_after_client_message(status: TicketStatus, expected: TicketStatus | None):
    assert status_after_client_message(status) is expected


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        pytest.param(TicketStatus.NEW, False, id="new"),
        pytest.param(TicketStatus.IN_PROGRESS, False, id="in-progress"),
        pytest.param(TicketStatus.WAITING_CLIENT, False, id="waiting-client"),
        pytest.param(TicketStatus.CLOSED, True, id="closed"),
        pytest.param(TicketStatus.REJECTED, False, id="rejected"),
    ],
)
def test_can_rate(status: TicketStatus, expected: bool):
    assert can_rate(status) is expected


def test_open_statuses():
    assert OPEN_STATUSES == {
        TicketStatus.NEW,
        TicketStatus.IN_PROGRESS,
        TicketStatus.WAITING_CLIENT,
    }


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        pytest.param(TicketStatus.NEW, True, id="new"),
        pytest.param(TicketStatus.IN_PROGRESS, True, id="in-progress"),
        pytest.param(TicketStatus.WAITING_CLIENT, True, id="waiting-client"),
        pytest.param(TicketStatus.CLOSED, False, id="closed"),
        pytest.param(TicketStatus.REJECTED, False, id="rejected"),
    ],
)
def test_is_open(status: TicketStatus, expected: bool):
    assert is_open(status) is expected


@pytest.mark.parametrize(
    ("last_client_message_at", "staff_seen_at", "expected"),
    [
        pytest.param(None, None, False, id="no-client-message"),
        pytest.param(None, NOW - timedelta(minutes=1), False, id="seen-without-message"),
        pytest.param(NOW, None, True, id="never-seen"),
        pytest.param(NOW, NOW - timedelta(minutes=1), True, id="seen-before"),
        pytest.param(NOW, NOW + timedelta(minutes=1), False, id="seen-after"),
        pytest.param(NOW, NOW, False, id="seen-at-the-same-time"),
    ],
)
def test_is_unread(
    last_client_message_at: datetime | None,
    staff_seen_at: datetime | None,
    expected: bool,
):
    assert is_unread(last_client_message_at, staff_seen_at) is expected


def test_route_reply_to_open_ticket_wins_over_active_and_several_open():
    result = route_client_message(
        reply_to_ticket_id=20,
        active_ticket_id=10,
        open_ticket_ids=[10, 20, 30],
    )
    assert result == ToTicket(ticket_id=20)


def test_route_reply_to_closed_ticket_falls_through_to_active():
    result = route_client_message(
        reply_to_ticket_id=99,
        active_ticket_id=20,
        open_ticket_ids=[10, 20],
    )
    assert result == ToTicket(ticket_id=20)


def test_route_open_active_ticket_without_reply():
    result = route_client_message(
        reply_to_ticket_id=None,
        active_ticket_id=20,
        open_ticket_ids=[10, 20, 30],
    )
    assert result == ToTicket(ticket_id=20)


def test_route_active_ticket_not_open_with_single_open_ticket():
    result = route_client_message(
        reply_to_ticket_id=None,
        active_ticket_id=99,
        open_ticket_ids=[10],
    )
    assert result == ToTicket(ticket_id=10)


def test_route_single_open_ticket_without_reply_or_active():
    result = route_client_message(
        reply_to_ticket_id=None,
        active_ticket_id=None,
        open_ticket_ids=[10],
    )
    assert result == ToTicket(ticket_id=10)


def test_route_several_open_tickets_without_reply_or_active():
    result = route_client_message(
        reply_to_ticket_id=None,
        active_ticket_id=None,
        open_ticket_ids=[30, 10, 20],
    )
    assert result == AskWhichTicket(ticket_ids=(30, 10, 20))


def test_route_several_open_tickets_with_closed_reply_and_active():
    result = route_client_message(
        reply_to_ticket_id=99,
        active_ticket_id=88,
        open_ticket_ids=[10, 20],
    )
    assert result == AskWhichTicket(ticket_ids=(10, 20))


def test_route_no_open_tickets_offers_new_question():
    result = route_client_message(
        reply_to_ticket_id=99,
        active_ticket_id=88,
        open_ticket_ids=[],
    )
    assert result == OfferNewQuestion()


def test_client_reopen_window_constant():
    assert CLIENT_REOPEN_WINDOW == timedelta(days=7)
