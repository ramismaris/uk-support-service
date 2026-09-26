from contextlib import ExitStack
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.constants import TicketStatus, TicketType, UserRole
from src.core.exceptions import (
    AppException,
    ConflictException,
    ForbiddenException,
    MessengerException,
    NotFoundException,
)
from src.core.texts import (
    RATING_INVALID,
    RATING_ONLY_CLOSED,
    REJECT_REASON_REQUIRED,
    STATUS_COMMENT_LIMIT,
    STATUS_COMMENT_TOO_LONG,
    TICKET_NOT_FOUND,
)
from src.services.status_service import StatusService


@pytest.fixture
def env() -> SimpleNamespace:
    db = AsyncMock()
    db.add = MagicMock()
    messenger = AsyncMock()

    client = MagicMock()
    client.id = 1
    client.max_user_id = 555

    staff = MagicMock()
    staff.id = 9
    staff.role = UserRole.MANAGER

    ticket = MagicMock()
    ticket.id = 1042
    ticket.status = TicketStatus.NEW
    ticket.type = TicketType.REQUEST
    ticket.client = client
    ticket.client_id = client.id
    ticket.closed_at = None
    ticket.assignee_id = None
    ticket.status_message_max_id = "card-1"

    tickets = MagicMock()
    tickets.get_by_id = AsyncMock(return_value=ticket)
    tickets.get_by_id_for_update = AsyncMock(return_value=ticket)

    changes = MagicMock()
    changes.create = AsyncMock()

    notifications = MagicMock()
    notifications.send_status_message = AsyncMock()
    notifications.update_status_card = AsyncMock()

    with ExitStack() as stack:
        stack.enter_context(
            patch("src.services.status_service.TicketRepository", return_value=tickets)
        )
        stack.enter_context(
            patch("src.services.status_service.StatusChangeRepository", return_value=changes)
        )
        stack.enter_context(
            patch(
                "src.services.status_service.NotificationService",
                return_value=notifications,
            )
        )
        publish = stack.enter_context(
            patch(
                "src.services.status_service.publish_ticket_updated",
                new_callable=AsyncMock,
            )
        )
        run_bg = stack.enter_context(patch("src.services.status_service.run_in_background"))
        notify = MagicMock(return_value="notify-coroutine")
        stack.enter_context(
            patch(
                "src.services.status_service.notify_staff_about_reopened_ticket",
                new=notify,
            )
        )
        service = StatusService(db, messenger)

        yield SimpleNamespace(
            db=db,
            messenger=messenger,
            client=client,
            staff=staff,
            ticket=ticket,
            tickets=tickets,
            changes=changes,
            notifications=notifications,
            publish=publish,
            run_bg=run_bg,
            notify=notify,
            service=service,
        )


def _assert_no_write(env: SimpleNamespace, *, looked_up: bool = True) -> None:
    if not looked_up:
        env.tickets.get_by_id_for_update.assert_not_awaited()
    env.changes.create.assert_not_awaited()
    env.db.commit.assert_not_awaited()
    env.notifications.send_status_message.assert_not_awaited()
    env.publish.assert_not_awaited()


def _assert_reopen_no_write(env: SimpleNamespace) -> None:
    env.changes.create.assert_not_awaited()
    env.db.commit.assert_not_awaited()
    env.notifications.update_status_card.assert_not_awaited()
    env.run_bg.assert_not_called()
    env.publish.assert_not_awaited()


# change_by_staff: transitions


async def test_change_by_staff_takes_new_ticket(env: SimpleNamespace) -> None:
    await env.service.change_by_staff(env.ticket.id, env.staff, TicketStatus.IN_PROGRESS, None)

    env.changes.create.assert_awaited_once_with(
        env.ticket.id,
        TicketStatus.NEW,
        TicketStatus.IN_PROGRESS,
        changed_by_id=env.staff.id,
        comment=None,
    )
    assert env.ticket.status == TicketStatus.IN_PROGRESS
    assert env.ticket.assignee_id == env.staff.id
    env.db.commit.assert_awaited_once()
    env.notifications.send_status_message.assert_awaited_once_with(env.ticket, None)
    env.publish.assert_awaited_once_with(env.db, env.ticket.id)
    env.tickets.get_by_id.assert_awaited_once_with(env.ticket.id, populate_existing=True)


async def test_change_by_staff_commits_then_sends_then_publishes(env: SimpleNamespace) -> None:
    order: list[str] = []
    env.db.commit.side_effect = lambda: order.append("commit")
    env.notifications.send_status_message.side_effect = lambda ticket, comment: order.append("send")
    env.publish.side_effect = lambda db, ticket_id: order.append("publish")

    await env.service.change_by_staff(env.ticket.id, env.staff, TicketStatus.IN_PROGRESS, None)

    assert order == ["commit", "send", "publish"]


@pytest.mark.parametrize(
    "status",
    [
        pytest.param(TicketStatus.IN_PROGRESS, id="in-progress"),
        pytest.param(TicketStatus.WAITING_CLIENT, id="waiting-client"),
    ],
)
async def test_change_by_staff_close_sets_closed_at(
    env: SimpleNamespace, status: TicketStatus
) -> None:
    env.ticket.status = status
    env.ticket.assignee_id = env.staff.id

    await env.service.change_by_staff(env.ticket.id, env.staff, TicketStatus.CLOSED, None)

    env.changes.create.assert_awaited_once_with(
        env.ticket.id,
        status,
        TicketStatus.CLOSED,
        changed_by_id=env.staff.id,
        comment=None,
    )
    assert env.ticket.status == TicketStatus.CLOSED
    assert env.ticket.closed_at is not None
    assert env.ticket.assignee_id == env.staff.id


@pytest.mark.parametrize(
    "status",
    [
        pytest.param(TicketStatus.NEW, id="new"),
        pytest.param(TicketStatus.IN_PROGRESS, id="in-progress"),
        pytest.param(TicketStatus.WAITING_CLIENT, id="waiting-client"),
    ],
)
async def test_change_by_staff_reject_sets_closed_at_and_reason(
    env: SimpleNamespace, status: TicketStatus
) -> None:
    env.ticket.status = status

    await env.service.change_by_staff(
        env.ticket.id, env.staff, TicketStatus.REJECTED, "Не наш профиль"
    )

    env.changes.create.assert_awaited_once_with(
        env.ticket.id,
        status,
        TicketStatus.REJECTED,
        changed_by_id=env.staff.id,
        comment="Не наш профиль",
    )
    assert env.ticket.status == TicketStatus.REJECTED
    assert env.ticket.closed_at is not None
    env.notifications.send_status_message.assert_awaited_once_with(env.ticket, "Не наш профиль")


@pytest.mark.parametrize(
    "status",
    [
        pytest.param(TicketStatus.CLOSED, id="closed"),
        pytest.param(TicketStatus.REJECTED, id="rejected"),
    ],
)
async def test_change_by_staff_admin_reopen_clears_closed_at_keeps_assignee(
    env: SimpleNamespace, status: TicketStatus
) -> None:
    env.ticket.status = status
    env.ticket.closed_at = datetime.now(UTC) - timedelta(days=30)
    env.ticket.assignee_id = 77
    env.staff.role = UserRole.ADMIN

    await env.service.change_by_staff(env.ticket.id, env.staff, TicketStatus.IN_PROGRESS, None)

    env.changes.create.assert_awaited_once_with(
        env.ticket.id,
        status,
        TicketStatus.IN_PROGRESS,
        changed_by_id=env.staff.id,
        comment=None,
    )
    assert env.ticket.status == TicketStatus.IN_PROGRESS
    assert env.ticket.closed_at is None
    assert env.ticket.assignee_id == 77


async def test_change_by_staff_waiting_client_keeps_assignee_and_closed_at(
    env: SimpleNamespace,
) -> None:
    env.ticket.status = TicketStatus.IN_PROGRESS
    env.ticket.assignee_id = 77

    await env.service.change_by_staff(env.ticket.id, env.staff, TicketStatus.WAITING_CLIENT, None)

    assert env.ticket.status == TicketStatus.WAITING_CLIENT
    assert env.ticket.assignee_id == 77
    assert env.ticket.closed_at is None


# change_by_staff: validation


@pytest.mark.parametrize(
    "comment",
    [
        pytest.param(None, id="none"),
        pytest.param("", id="empty"),
        pytest.param("   ", id="blank"),
    ],
)
async def test_change_by_staff_reject_requires_reason(
    env: SimpleNamespace, comment: str | None
) -> None:
    env.ticket.status = TicketStatus.IN_PROGRESS

    with pytest.raises(AppException) as exc:
        await env.service.change_by_staff(env.ticket.id, env.staff, TicketStatus.REJECTED, comment)

    assert exc.value.status_code == 400
    assert exc.value.message == REJECT_REASON_REQUIRED
    _assert_no_write(env, looked_up=False)


async def test_change_by_staff_rejects_over_limit_comment(env: SimpleNamespace) -> None:
    env.ticket.status = TicketStatus.IN_PROGRESS

    with pytest.raises(AppException) as exc:
        await env.service.change_by_staff(
            env.ticket.id,
            env.staff,
            TicketStatus.WAITING_CLIENT,
            "а" * (STATUS_COMMENT_LIMIT + 1),
        )

    assert exc.value.status_code == 400
    assert exc.value.message == STATUS_COMMENT_TOO_LONG
    _assert_no_write(env, looked_up=False)


async def test_change_by_staff_accepts_limit_comment(env: SimpleNamespace) -> None:
    comment = "а" * STATUS_COMMENT_LIMIT
    env.ticket.status = TicketStatus.IN_PROGRESS

    await env.service.change_by_staff(
        env.ticket.id, env.staff, TicketStatus.WAITING_CLIENT, comment
    )

    env.changes.create.assert_awaited_once_with(
        env.ticket.id,
        TicketStatus.IN_PROGRESS,
        TicketStatus.WAITING_CLIENT,
        changed_by_id=env.staff.id,
        comment=comment,
    )
    env.notifications.send_status_message.assert_awaited_once_with(env.ticket, comment)


async def test_change_by_staff_missing_ticket(env: SimpleNamespace) -> None:
    env.tickets.get_by_id_for_update.return_value = None

    with pytest.raises(NotFoundException) as exc:
        await env.service.change_by_staff(env.ticket.id, env.staff, TicketStatus.IN_PROGRESS, None)

    assert exc.value.message == TICKET_NOT_FOUND
    _assert_no_write(env)


async def test_change_by_staff_invalid_transition(env: SimpleNamespace) -> None:
    with pytest.raises(ConflictException) as exc:
        await env.service.change_by_staff(env.ticket.id, env.staff, TicketStatus.CLOSED, None)

    assert exc.value.status_code == 409
    _assert_no_write(env)


@pytest.mark.parametrize(
    "status",
    [
        pytest.param(TicketStatus.CLOSED, id="closed"),
        pytest.param(TicketStatus.REJECTED, id="rejected"),
    ],
)
async def test_change_by_staff_manager_cannot_reopen(
    env: SimpleNamespace, status: TicketStatus
) -> None:
    env.ticket.status = status
    env.ticket.closed_at = datetime.now(UTC) - timedelta(days=1)

    with pytest.raises(ForbiddenException) as exc:
        await env.service.change_by_staff(env.ticket.id, env.staff, TicketStatus.IN_PROGRESS, None)

    assert exc.value.status_code == 403
    _assert_no_write(env)


async def test_change_by_staff_send_failure_still_commits_and_publishes(
    env: SimpleNamespace,
) -> None:
    env.notifications.send_status_message.side_effect = MessengerException()

    await env.service.change_by_staff(env.ticket.id, env.staff, TicketStatus.IN_PROGRESS, None)

    assert env.ticket.status == TicketStatus.IN_PROGRESS
    env.db.commit.assert_awaited_once()
    env.publish.assert_awaited_once_with(env.db, env.ticket.id)


# reopen_by_client


async def test_reopen_by_client_reopens_own_closed_ticket(env: SimpleNamespace) -> None:
    env.ticket.status = TicketStatus.CLOSED
    env.ticket.closed_at = datetime.now(UTC) - timedelta(days=1)
    env.ticket.assignee_id = 77

    await env.service.reopen_by_client(env.client, env.ticket.id)

    env.changes.create.assert_awaited_once_with(
        env.ticket.id,
        TicketStatus.CLOSED,
        TicketStatus.IN_PROGRESS,
        changed_by_id=env.client.id,
        comment=None,
    )
    assert env.ticket.status == TicketStatus.IN_PROGRESS
    assert env.ticket.closed_at is None
    assert env.ticket.assignee_id == 77
    env.db.commit.assert_awaited_once()
    env.notifications.update_status_card.assert_awaited_once_with(env.ticket)
    env.notifications.send_status_message.assert_not_awaited()
    env.run_bg.assert_called_once_with(
        env.notify.return_value, name=f"notify-reopened-{env.ticket.id}"
    )
    env.notify.assert_called_once_with(env.ticket.id)
    env.publish.assert_awaited_once_with(env.db, env.ticket.id)


async def test_reopen_by_client_foreign_ticket(env: SimpleNamespace) -> None:
    env.ticket.status = TicketStatus.CLOSED
    env.ticket.closed_at = datetime.now(UTC) - timedelta(days=1)
    env.ticket.client_id = env.client.id + 1

    with pytest.raises(NotFoundException):
        await env.service.reopen_by_client(env.client, env.ticket.id)

    _assert_reopen_no_write(env)


async def test_reopen_by_client_missing_ticket(env: SimpleNamespace) -> None:
    env.tickets.get_by_id_for_update.return_value = None

    with pytest.raises(NotFoundException):
        await env.service.reopen_by_client(env.client, env.ticket.id)

    _assert_reopen_no_write(env)


# A client reopening a NEW ticket gets 403, not 409: NEW -> IN_PROGRESS is a
# valid staff transition, so the client simply lacks the role. The "not closed"
# conflict is checked with the statuses where the transition itself is invalid.
@pytest.mark.parametrize(
    "status",
    [
        pytest.param(TicketStatus.IN_PROGRESS, id="in-progress"),
        pytest.param(TicketStatus.WAITING_CLIENT, id="waiting-client"),
    ],
)
async def test_reopen_by_client_not_closed(env: SimpleNamespace, status: TicketStatus) -> None:
    env.ticket.status = status

    with pytest.raises(ConflictException) as exc:
        await env.service.reopen_by_client(env.client, env.ticket.id)

    assert exc.value.status_code == 409
    _assert_reopen_no_write(env)


async def test_reopen_by_client_rejected_is_forbidden(env: SimpleNamespace) -> None:
    env.ticket.status = TicketStatus.REJECTED
    env.ticket.closed_at = datetime.now(UTC) - timedelta(days=1)

    with pytest.raises(ForbiddenException) as exc:
        await env.service.reopen_by_client(env.client, env.ticket.id)

    assert exc.value.status_code == 403
    _assert_reopen_no_write(env)


async def test_reopen_by_client_after_window(env: SimpleNamespace) -> None:
    env.ticket.status = TicketStatus.CLOSED
    env.ticket.closed_at = datetime.now(UTC) - timedelta(days=7, seconds=1)

    with pytest.raises(ConflictException) as exc:
        await env.service.reopen_by_client(env.client, env.ticket.id)

    assert exc.value.status_code == 409
    assert "Прошло больше 7 дней" in exc.value.message
    _assert_reopen_no_write(env)


async def test_reopen_by_client_card_failure_logged_and_continues(env: SimpleNamespace) -> None:
    env.ticket.status = TicketStatus.CLOSED
    env.ticket.closed_at = datetime.now(UTC) - timedelta(days=1)
    env.notifications.update_status_card.side_effect = MessengerException()

    await env.service.reopen_by_client(env.client, env.ticket.id)

    assert env.ticket.status == TicketStatus.IN_PROGRESS
    env.db.commit.assert_awaited_once()
    env.run_bg.assert_called_once()
    env.publish.assert_awaited_once_with(env.db, env.ticket.id)


# rate


@pytest.mark.parametrize(
    "score",
    [
        pytest.param(1, id="one"),
        pytest.param(5, id="five"),
    ],
)
async def test_rate_accepts_and_overwrites_earlier_rating(env: SimpleNamespace, score: int) -> None:
    env.ticket.status = TicketStatus.CLOSED
    env.ticket.rating = 3

    result = await env.service.rate(env.client, env.ticket.id, score)

    assert result is env.ticket
    assert env.ticket.rating == score
    env.db.commit.assert_awaited_once()
    env.publish.assert_awaited_once_with(env.db, env.ticket.id)


async def test_rate_publishes_after_commit(env: SimpleNamespace) -> None:
    env.ticket.status = TicketStatus.CLOSED
    order: list[str] = []
    env.db.commit.side_effect = lambda: order.append("commit")
    env.publish.side_effect = lambda db, ticket_id: order.append("publish")

    await env.service.rate(env.client, env.ticket.id, 4)

    assert order == ["commit", "publish"]


@pytest.mark.parametrize(
    "score",
    [
        pytest.param(0, id="zero"),
        pytest.param(6, id="six"),
    ],
)
async def test_rate_rejects_invalid_score(env: SimpleNamespace, score: int) -> None:
    with pytest.raises(AppException) as exc:
        await env.service.rate(env.client, env.ticket.id, score)

    assert exc.value.status_code == 400
    assert exc.value.message == RATING_INVALID
    env.tickets.get_by_id.assert_not_awaited()
    env.db.commit.assert_not_awaited()
    env.publish.assert_not_awaited()


async def test_rate_foreign_ticket(env: SimpleNamespace) -> None:
    env.ticket.status = TicketStatus.CLOSED
    env.ticket.client_id = env.client.id + 1

    with pytest.raises(NotFoundException):
        await env.service.rate(env.client, env.ticket.id, 5)

    env.db.commit.assert_not_awaited()
    env.publish.assert_not_awaited()


async def test_rate_missing_ticket(env: SimpleNamespace) -> None:
    env.tickets.get_by_id.return_value = None

    with pytest.raises(NotFoundException):
        await env.service.rate(env.client, env.ticket.id, 5)

    env.db.commit.assert_not_awaited()
    env.publish.assert_not_awaited()


@pytest.mark.parametrize(
    "status",
    [
        pytest.param(TicketStatus.NEW, id="new"),
        pytest.param(TicketStatus.IN_PROGRESS, id="in-progress"),
        pytest.param(TicketStatus.WAITING_CLIENT, id="waiting-client"),
        pytest.param(TicketStatus.REJECTED, id="rejected"),
    ],
)
async def test_rate_not_closed(env: SimpleNamespace, status: TicketStatus) -> None:
    env.ticket.status = status

    with pytest.raises(ConflictException) as exc:
        await env.service.rate(env.client, env.ticket.id, 5)

    assert exc.value.status_code == 409
    assert exc.value.message == RATING_ONLY_CLOSED
    env.db.commit.assert_not_awaited()
    env.publish.assert_not_awaited()
