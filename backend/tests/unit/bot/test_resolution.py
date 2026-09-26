from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from maxapi.types import MessageCallback
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.handlers import resolution
from src.bot.keyboards import FORM_START, RATE_PREFIX
from src.core.constants import RESOLVED_NO_PREFIX, RESOLVED_YES_PREFIX, TicketType
from src.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from src.core.texts import (
    OUTDATED_BUTTON_TEXT,
    RATE_PROMPT,
    RATE_THANKS,
    RATING_ONLY_CLOSED,
    REOPENED_TEXT,
    TICKET_NOT_FOUND,
    ticket_dative,
    ticket_genitive,
)

TICKET_ID = 1042
QUESTION_ID = 1051

NOT_CLOSED_MESSAGE = "Обращение уже не закрыто"


def _user() -> MagicMock:
    user = MagicMock()
    user.id = 1
    user.max_user_id = 42
    return user


def _ticket(
    ticket_id: int = TICKET_ID, ticket_type: TicketType = TicketType.REQUEST
) -> SimpleNamespace:
    return SimpleNamespace(id=ticket_id, type=ticket_type)


def _callback(payload: str) -> MagicMock:
    event = MagicMock(spec=MessageCallback)
    event.edit = AsyncMock()
    event.ack = AsyncMock()
    callback = MagicMock()
    callback.payload = payload
    event.callback = callback
    return event


def _db() -> MagicMock:
    return MagicMock(spec=AsyncSession)


def _edit_text(event: MagicMock) -> str:
    return event.edit.await_args.kwargs["text"]


def _edit_rows(event: MagicMock) -> list:
    return event.edit.await_args.kwargs["attachments"][0].payload.buttons


@pytest.fixture
def services() -> SimpleNamespace:
    client_service = MagicMock()
    client_service.get_ticket = AsyncMock(return_value=_ticket())
    client_service.set_active_ticket = AsyncMock(return_value=_ticket())
    status_service = MagicMock()
    status_service.rate = AsyncMock(return_value=_ticket())
    status_service.reopen_by_client = AsyncMock(return_value=_ticket())

    with (
        patch("src.bot.handlers.resolution.ClientTicketService", return_value=client_service),
        patch("src.bot.handlers.resolution.StatusService", return_value=status_service),
    ):
        yield SimpleNamespace(client=client_service, status=status_service)


async def test_resolved_yes_asks_for_rating(services: SimpleNamespace) -> None:
    event = _callback(f"{RESOLVED_YES_PREFIX}{TICKET_ID}")
    user = _user()

    await resolution.handle_resolved_yes(event, _db(), user)

    services.client.get_ticket.assert_awaited_once_with(user, TICKET_ID)
    assert _edit_text(event) == RATE_PROMPT.format(
        label=ticket_dative(TicketType.REQUEST, TICKET_ID)
    )
    rows = _edit_rows(event)
    assert [button.text for button in rows[0]] == ["1", "2", "3", "4", "5"]
    assert [button.payload for button in rows[0]] == [
        f"{RATE_PREFIX}{TICKET_ID}:{score}" for score in range(1, 6)
    ]
    event.ack.assert_not_awaited()


async def test_resolved_yes_uses_question_label(services: SimpleNamespace) -> None:
    services.client.get_ticket.return_value = _ticket(QUESTION_ID, TicketType.QUESTION)
    event = _callback(f"{RESOLVED_YES_PREFIX}{QUESTION_ID}")

    await resolution.handle_resolved_yes(event, _db(), _user())

    assert _edit_text(event) == RATE_PROMPT.format(
        label=ticket_dative(TicketType.QUESTION, QUESTION_ID)
    )


async def test_resolved_yes_other_client_acks(services: SimpleNamespace) -> None:
    services.client.get_ticket.side_effect = NotFoundException(TICKET_NOT_FOUND)
    event = _callback(f"{RESOLVED_YES_PREFIX}{TICKET_ID}")

    await resolution.handle_resolved_yes(event, _db(), _user())

    event.ack.assert_awaited_once_with(notification=TICKET_NOT_FOUND)
    event.edit.assert_not_awaited()


@pytest.mark.parametrize(
    "payload",
    [
        f"{RESOLVED_YES_PREFIX}abc",
        f"{RESOLVED_YES_PREFIX}0",
        f"{RESOLVED_YES_PREFIX}{2**63}",
    ],
)
async def test_resolved_yes_bad_id_acks(services: SimpleNamespace, payload: str) -> None:
    event = _callback(payload)

    await resolution.handle_resolved_yes(event, _db(), _user())

    event.ack.assert_awaited_once_with(notification=OUTDATED_BUTTON_TEXT)
    services.client.get_ticket.assert_not_awaited()
    event.edit.assert_not_awaited()


async def test_resolved_yes_outdated_message_acks(services: SimpleNamespace) -> None:
    event = _callback(f"{RESOLVED_YES_PREFIX}{TICKET_ID}")
    event.edit.side_effect = ValueError("message not found")

    await resolution.handle_resolved_yes(event, _db(), _user())

    event.ack.assert_awaited_once_with(notification=OUTDATED_BUTTON_TEXT)


async def test_rate_saves_score(services: SimpleNamespace) -> None:
    event = _callback(f"{RATE_PREFIX}{TICKET_ID}:5")
    user = _user()

    await resolution.handle_rate(event, _db(), user)

    services.status.rate.assert_awaited_once_with(user, TICKET_ID, 5)
    assert _edit_text(event) == RATE_THANKS
    event.ack.assert_not_awaited()


async def test_rate_not_closed_acks(services: SimpleNamespace) -> None:
    services.status.rate.side_effect = ConflictException(RATING_ONLY_CLOSED)
    event = _callback(f"{RATE_PREFIX}{TICKET_ID}:4")

    await resolution.handle_rate(event, _db(), _user())

    event.ack.assert_awaited_once_with(notification=RATING_ONLY_CLOSED)
    event.edit.assert_not_awaited()


async def test_rate_other_client_acks(services: SimpleNamespace) -> None:
    services.status.rate.side_effect = NotFoundException(TICKET_NOT_FOUND)
    event = _callback(f"{RATE_PREFIX}{TICKET_ID}:3")

    await resolution.handle_rate(event, _db(), _user())

    event.ack.assert_awaited_once_with(notification=TICKET_NOT_FOUND)
    event.edit.assert_not_awaited()


async def test_rate_outdated_message_acks(services: SimpleNamespace) -> None:
    event = _callback(f"{RATE_PREFIX}{TICKET_ID}:3")
    event.edit.side_effect = ValueError("message not found")

    await resolution.handle_rate(event, _db(), _user())

    event.ack.assert_awaited_once_with(notification=OUTDATED_BUTTON_TEXT)


@pytest.mark.parametrize(
    "payload",
    [
        f"{RATE_PREFIX}{TICKET_ID}:0",
        f"{RATE_PREFIX}{TICKET_ID}:6",
        f"{RATE_PREFIX}{TICKET_ID}:x",
        f"{RATE_PREFIX}{TICKET_ID}:",
        f"{RATE_PREFIX}{TICKET_ID}",
        f"{RATE_PREFIX}{TICKET_ID}:5:6",
        f"{RATE_PREFIX}abc:5",
        f"{RATE_PREFIX}0:5",
        f"{RATE_PREFIX}{2**63}:5",
    ],
)
async def test_rate_invalid_payload_acks(services: SimpleNamespace, payload: str) -> None:
    event = _callback(payload)

    await resolution.handle_rate(event, _db(), _user())

    event.ack.assert_awaited_once_with(notification=OUTDATED_BUTTON_TEXT)
    services.status.rate.assert_not_awaited()
    event.edit.assert_not_awaited()


async def test_resolved_no_reopens_and_makes_active(services: SimpleNamespace) -> None:
    calls: list[str] = []
    services.status.reopen_by_client.side_effect = lambda *args: calls.append("reopen") or _ticket()
    services.client.set_active_ticket.side_effect = lambda *args: (
        calls.append("active") or _ticket()
    )
    event = _callback(f"{RESOLVED_NO_PREFIX}{TICKET_ID}")
    user = _user()

    await resolution.handle_resolved_no(event, _db(), user)

    services.status.reopen_by_client.assert_awaited_once_with(user, TICKET_ID)
    services.client.set_active_ticket.assert_awaited_once_with(user, TICKET_ID)
    # The ticket must be open again before it can become the active one.
    assert calls == ["reopen", "active"]
    assert _edit_text(event) == REOPENED_TEXT.format(
        label=ticket_genitive(TicketType.REQUEST, TICKET_ID)
    )
    assert event.edit.await_args.kwargs["attachments"] == []
    event.ack.assert_not_awaited()


async def test_resolved_no_uses_question_label(services: SimpleNamespace) -> None:
    services.status.reopen_by_client.return_value = _ticket(QUESTION_ID, TicketType.QUESTION)
    event = _callback(f"{RESOLVED_NO_PREFIX}{QUESTION_ID}")

    await resolution.handle_resolved_no(event, _db(), _user())

    assert _edit_text(event) == REOPENED_TEXT.format(
        label=ticket_genitive(TicketType.QUESTION, QUESTION_ID)
    )


async def test_resolved_no_after_window_offers_menu(services: SimpleNamespace) -> None:
    message = "Прошло больше 7 дней после закрытия — создайте новое обращение"
    services.status.reopen_by_client.side_effect = ConflictException(message)
    event = _callback(f"{RESOLVED_NO_PREFIX}{TICKET_ID}")

    await resolution.handle_resolved_no(event, _db(), _user())

    assert _edit_text(event) == message
    assert _edit_rows(event)[0][0].payload == FORM_START
    services.client.set_active_ticket.assert_not_awaited()


async def test_resolved_no_when_not_closed_offers_menu(services: SimpleNamespace) -> None:
    services.status.reopen_by_client.side_effect = ForbiddenException(NOT_CLOSED_MESSAGE)
    event = _callback(f"{RESOLVED_NO_PREFIX}{TICKET_ID}")

    await resolution.handle_resolved_no(event, _db(), _user())

    assert _edit_text(event) == NOT_CLOSED_MESSAGE
    assert _edit_rows(event)[0][0].payload == FORM_START
    services.client.set_active_ticket.assert_not_awaited()


async def test_resolved_no_other_client_offers_menu(services: SimpleNamespace) -> None:
    services.status.reopen_by_client.side_effect = NotFoundException(TICKET_NOT_FOUND)
    event = _callback(f"{RESOLVED_NO_PREFIX}{TICKET_ID}")

    await resolution.handle_resolved_no(event, _db(), _user())

    assert _edit_text(event) == TICKET_NOT_FOUND
    assert _edit_rows(event)[0][0].payload == FORM_START
    services.client.set_active_ticket.assert_not_awaited()


async def test_resolved_no_outdated_message_acks(services: SimpleNamespace) -> None:
    event = _callback(f"{RESOLVED_NO_PREFIX}{TICKET_ID}")
    event.edit.side_effect = ValueError("message not found")

    await resolution.handle_resolved_no(event, _db(), _user())

    event.ack.assert_awaited_once_with(notification=OUTDATED_BUTTON_TEXT)


@pytest.mark.parametrize(
    "payload",
    [
        f"{RESOLVED_NO_PREFIX}abc",
        f"{RESOLVED_NO_PREFIX}0",
        f"{RESOLVED_NO_PREFIX}{2**63}",
    ],
)
async def test_resolved_no_bad_id_acks(services: SimpleNamespace, payload: str) -> None:
    event = _callback(payload)

    await resolution.handle_resolved_no(event, _db(), _user())

    event.ack.assert_awaited_once_with(notification=OUTDATED_BUTTON_TEXT)
    services.status.reopen_by_client.assert_not_awaited()
    event.edit.assert_not_awaited()


async def test_stale_resolution_callback_acks() -> None:
    event = _callback("resolved:other:1")

    await resolution.handle_stale_resolution(event)

    event.ack.assert_awaited_once_with(notification=OUTDATED_BUTTON_TEXT)
