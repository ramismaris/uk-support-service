from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from src.core.constants import TicketStatus, TicketType
from src.models.building import Building
from src.models.category import Category
from src.models.status_change import StatusChange
from src.models.ticket import Ticket
from src.services.status_card import build_status_card

TZ = ZoneInfo("Europe/Moscow")


def _ticket(**overrides) -> Ticket:
    values = {
        "id": 1042,
        "type": TicketType.REQUEST,
        "status": TicketStatus.NEW,
        "client_id": 1,
        "description": "Течёт кран",
        "category_id": 1,
        "building_id": 1,
        "apartment": "45",
    }
    values.update(overrides)
    ticket = Ticket(**values)
    if ticket.type == TicketType.REQUEST:
        ticket.category = Category(id=1, title="Сантехника", sort_order=1)
        ticket.building = Building(id=1, address="ул. Ленина, 12")
    return ticket


def _change(to_status: TicketStatus, at: datetime) -> StatusChange:
    return StatusChange(ticket_id=1042, from_status=None, to_status=to_status, created_at=at)


def test_new_request_card_shows_moscow_time() -> None:
    ticket = _ticket()
    history = [_change(TicketStatus.NEW, datetime(2026, 9, 25, 9, 4, tzinfo=UTC))]

    card = build_status_card(ticket, history, TZ)

    assert card == (
        "**Заявка №1042** · Сантехника\n"
        "ул. Ленина, 12, кв. 45\n"
        "\n"
        "🟢 Принята — 25.09 12:04\n"
        "⚪ В работе\n"
        "⚪ Закрыта"
    )


def test_question_card_has_no_address_line() -> None:
    ticket = _ticket(
        id=1047,
        type=TicketType.QUESTION,
        category_id=None,
        building_id=None,
        apartment=None,
    )
    history = [_change(TicketStatus.NEW, datetime(2026, 9, 25, 9, 4, tzinfo=UTC))]

    card = build_status_card(ticket, history, TZ)

    assert card == ("**Вопрос №1047**\n\n🟢 Принята — 25.09 12:04\n⚪ В работе\n⚪ Закрыта")


def test_closed_card_shows_full_timeline_and_no_pending_steps() -> None:
    ticket = _ticket(status=TicketStatus.CLOSED)
    history = [
        _change(TicketStatus.NEW, datetime(2026, 9, 25, 9, 4, tzinfo=UTC)),
        _change(TicketStatus.IN_PROGRESS, datetime(2026, 9, 25, 9, 30, tzinfo=UTC)),
        _change(TicketStatus.WAITING_CLIENT, datetime(2026, 9, 25, 10, 0, tzinfo=UTC)),
        _change(TicketStatus.CLOSED, datetime(2026, 9, 26, 9, 0, tzinfo=UTC)),
    ]

    card = build_status_card(ticket, history, TZ)

    assert card == (
        "**Заявка №1042** · Сантехника\n"
        "ул. Ленина, 12, кв. 45\n"
        "\n"
        "🟢 Принята — 25.09 12:04\n"
        "🟢 В работе — 25.09 12:30\n"
        "🟡 Нужен ваш ответ — 25.09 13:00\n"
        "🟢 Закрыта — 26.09 12:00"
    )
    assert "⚪" not in card


def test_rejected_card_has_red_icon_and_no_pending_steps() -> None:
    ticket = _ticket(status=TicketStatus.REJECTED)
    history = [
        _change(TicketStatus.NEW, datetime(2026, 9, 25, 9, 4, tzinfo=UTC)),
        _change(TicketStatus.REJECTED, datetime(2026, 9, 25, 9, 30, tzinfo=UTC)),
    ]

    card = build_status_card(ticket, history, TZ)

    assert "🔴 Отклонена — 25.09 12:30" in card
    assert "⚪" not in card


@pytest.mark.parametrize(
    ("status", "pending"),
    [
        (TicketStatus.NEW, ["⚪ В работе", "⚪ Закрыта"]),
        (TicketStatus.IN_PROGRESS, ["⚪ Закрыта"]),
        (TicketStatus.WAITING_CLIENT, ["⚪ Закрыта"]),
        (TicketStatus.CLOSED, []),
        (TicketStatus.REJECTED, []),
    ],
)
def test_pending_steps_depend_on_current_status(status: TicketStatus, pending: list[str]) -> None:
    ticket = _ticket(status=status)
    history = [_change(TicketStatus.NEW, datetime(2026, 9, 25, 9, 4, tzinfo=UTC))]
    if status != TicketStatus.NEW:
        history.append(_change(status, datetime(2026, 9, 25, 9, 30, tzinfo=UTC)))

    lines = build_status_card(ticket, history, TZ).splitlines()

    assert [line for line in lines if line.startswith("⚪")] == pending
