import logging
from contextlib import ExitStack
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.constants import SenderType, TicketPriority, TicketStatus, TicketType
from src.models.message import Message
from src.models.ticket import Ticket
from src.schemas.message import MessageResponse
from src.schemas.ticket import TicketListItemResponse
from src.services import events

NOW = datetime(2026, 9, 25, 12, 0, tzinfo=UTC)


def _ticket() -> Ticket:
    ticket = Ticket(
        id=1042,
        type=TicketType.REQUEST,
        status=TicketStatus.IN_PROGRESS,
        priority=TicketPriority.NORMAL,
        description="Течёт кран",
        apartment="45",
        created_at=NOW,
        last_client_message_at=NOW,
    )
    ticket.client = SimpleNamespace(id=1, first_name="Мария", last_name=None)
    ticket.assignee = SimpleNamespace(id=9, first_name="Игорь", last_name=None)
    ticket.category = None
    ticket.building = None
    return ticket


def _message() -> Message:
    message = Message(
        id=77,
        ticket_id=1042,
        sender_type=SenderType.STAFF,
        text="Мастер придёт завтра",
        created_at=NOW,
    )
    message.author = SimpleNamespace(id=9, first_name="Игорь", last_name=None)
    message.files = []
    return message


@pytest.fixture
def env() -> SimpleNamespace:
    db = AsyncMock()
    ticket = _ticket()
    message = _message()

    tickets_repo = MagicMock()
    tickets_repo.get_by_id = AsyncMock(return_value=ticket)
    messages_repo = MagicMock()
    messages_repo.get_by_id = AsyncMock(return_value=message)

    with ExitStack() as stack:
        stack.enter_context(
            patch("src.services.events.TicketRepository", return_value=tickets_repo)
        )
        stack.enter_context(
            patch("src.services.events.MessageRepository", return_value=messages_repo)
        )
        run_bg = stack.enter_context(patch("src.services.events.run_in_background"))
        manager = stack.enter_context(patch("src.services.events.ws_manager"))

        yield SimpleNamespace(
            db=db,
            ticket=ticket,
            message=message,
            tickets_repo=tickets_repo,
            messages_repo=messages_repo,
            run_bg=run_bg,
            manager=manager,
        )


def _ticket_payload(ticket: Ticket, event_type: str) -> dict:
    return {
        "type": event_type,
        "ticket": TicketListItemResponse.model_validate(ticket).model_dump(mode="json"),
    }


async def test_publish_ticket_created_reads_fresh_and_schedules(env: SimpleNamespace) -> None:
    await events.publish_ticket_created(env.db, env.ticket.id)

    env.tickets_repo.get_by_id.assert_awaited_once_with(env.ticket.id, populate_existing=True)
    payload = _ticket_payload(env.ticket, "ticket_created")
    assert set(payload) == {"type", "ticket"}
    env.manager.broadcast.assert_called_once_with(payload)
    env.run_bg.assert_called_once_with(
        env.manager.broadcast.return_value, name=f"ws-ticket-created-{env.ticket.id}"
    )


async def test_publish_ticket_updated_reads_fresh_and_schedules(env: SimpleNamespace) -> None:
    await events.publish_ticket_updated(env.db, env.ticket.id)

    env.tickets_repo.get_by_id.assert_awaited_once_with(env.ticket.id, populate_existing=True)
    payload = _ticket_payload(env.ticket, "ticket_updated")
    assert set(payload) == {"type", "ticket"}
    env.manager.broadcast.assert_called_once_with(payload)
    env.run_bg.assert_called_once_with(
        env.manager.broadcast.return_value, name=f"ws-ticket-updated-{env.ticket.id}"
    )


async def test_publish_message_created_reads_fresh_and_schedules(env: SimpleNamespace) -> None:
    await events.publish_message_created(env.db, env.message.id)

    env.messages_repo.get_by_id.assert_awaited_once_with(env.message.id, populate_existing=True)
    payload = {
        "type": "message_created",
        "message": MessageResponse.model_validate(env.message).model_dump(mode="json"),
    }
    assert set(payload) == {"type", "message"}
    env.manager.broadcast.assert_called_once_with(payload)
    env.run_bg.assert_called_once_with(
        env.manager.broadcast.return_value, name=f"ws-message-created-{env.message.id}"
    )


async def test_publish_ticket_missing_logs_and_schedules_nothing(
    env: SimpleNamespace, caplog: pytest.LogCaptureFixture
) -> None:
    env.tickets_repo.get_by_id.return_value = None

    with caplog.at_level(logging.WARNING, logger="src.services.events"):
        await events.publish_ticket_created(env.db, env.ticket.id)

    env.run_bg.assert_not_called()
    assert str(env.ticket.id) in caplog.text


async def test_publish_message_missing_logs_and_schedules_nothing(
    env: SimpleNamespace, caplog: pytest.LogCaptureFixture
) -> None:
    env.messages_repo.get_by_id.return_value = None

    with caplog.at_level(logging.WARNING, logger="src.services.events"):
        await events.publish_message_created(env.db, env.message.id)

    env.run_bg.assert_not_called()
    assert str(env.message.id) in caplog.text


async def test_publish_ticket_build_error_is_logged_not_raised(
    env: SimpleNamespace, caplog: pytest.LogCaptureFixture
) -> None:
    env.tickets_repo.get_by_id.side_effect = RuntimeError("db down")

    with caplog.at_level(logging.ERROR, logger="src.services.events"):
        await events.publish_ticket_updated(env.db, env.ticket.id)

    env.run_bg.assert_not_called()
    assert "db down" in caplog.text


async def test_publish_message_build_error_is_logged_not_raised(
    env: SimpleNamespace, caplog: pytest.LogCaptureFixture
) -> None:
    env.messages_repo.get_by_id.side_effect = RuntimeError("db down")

    with caplog.at_level(logging.ERROR, logger="src.services.events"):
        await events.publish_message_created(env.db, env.message.id)

    env.run_bg.assert_not_called()
    assert "db down" in caplog.text
