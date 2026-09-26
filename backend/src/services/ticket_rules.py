from dataclasses import dataclass
from datetime import datetime, timedelta

from src.core.constants import TicketStatus, UserRole
from src.core.exceptions import ConflictException, ForbiddenException

OPEN_STATUSES: frozenset[TicketStatus] = frozenset(
    {
        TicketStatus.NEW,
        TicketStatus.IN_PROGRESS,
        TicketStatus.WAITING_CLIENT,
    }
)

CLIENT_REOPEN_WINDOW = timedelta(days=7)

# Transitions available to a person (panel action or the client's button).
# System transitions are handled by status_after_staff_message /
# status_after_client_message.
_PERSON_TRANSITIONS: dict[tuple[TicketStatus, TicketStatus], frozenset[UserRole]] = {
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

_INVALID_TRANSITION_MESSAGE = "Нельзя перевести обращение в этот статус"
_FORBIDDEN_TRANSITION_MESSAGE = "Недостаточно прав для этого действия"
_REOPEN_WINDOW_EXPIRED_MESSAGE = "Прошло больше 7 дней после закрытия — создайте новое обращение"


def is_open(status: TicketStatus) -> bool:
    return status in OPEN_STATUSES


def is_unread(
    last_client_message_at: datetime | None,
    staff_seen_at: datetime | None,
) -> bool:
    if last_client_message_at is None:
        return False
    return staff_seen_at is None or last_client_message_at > staff_seen_at


def can_client_reopen(status: TicketStatus, closed_at: datetime | None, now: datetime) -> bool:
    if status != TicketStatus.CLOSED or closed_at is None:
        return False
    return now - closed_at <= CLIENT_REOPEN_WINDOW


def check_transition(
    current: TicketStatus,
    target: TicketStatus,
    acting_as: UserRole,
    *,
    closed_at: datetime | None,
    now: datetime,
) -> None:
    allowed_roles = _PERSON_TRANSITIONS.get((current, target))
    if allowed_roles is None:
        raise ConflictException(_INVALID_TRANSITION_MESSAGE)
    if acting_as not in allowed_roles:
        raise ForbiddenException(_FORBIDDEN_TRANSITION_MESSAGE)
    if (
        acting_as == UserRole.CLIENT
        and current == TicketStatus.CLOSED
        and target == TicketStatus.IN_PROGRESS
        and not can_client_reopen(current, closed_at, now)
    ):
        raise ConflictException(_REOPEN_WINDOW_EXPIRED_MESSAGE)


def status_after_staff_message(status: TicketStatus) -> TicketStatus | None:
    if status == TicketStatus.NEW:
        return TicketStatus.IN_PROGRESS
    return None


def status_after_client_message(status: TicketStatus) -> TicketStatus | None:
    if status == TicketStatus.WAITING_CLIENT:
        return TicketStatus.IN_PROGRESS
    return None


def can_rate(status: TicketStatus) -> bool:
    return status == TicketStatus.CLOSED


@dataclass(frozen=True)
class ToTicket:
    ticket_id: int


@dataclass(frozen=True)
class AskWhichTicket:
    ticket_ids: tuple[int, ...]


@dataclass(frozen=True)
class OfferNewQuestion:
    pass


def route_client_message(
    reply_to_ticket_id: int | None,
    active_ticket_id: int | None,
    open_ticket_ids: list[int],
) -> ToTicket | AskWhichTicket | OfferNewQuestion:
    if reply_to_ticket_id is not None and reply_to_ticket_id in open_ticket_ids:
        return ToTicket(reply_to_ticket_id)
    if active_ticket_id is not None and active_ticket_id in open_ticket_ids:
        return ToTicket(active_ticket_id)
    if len(open_ticket_ids) == 1:
        return ToTicket(open_ticket_ids[0])
    if len(open_ticket_ids) > 1:
        return AskWhichTicket(tuple(open_ticket_ids))
    return OfferNewQuestion()
