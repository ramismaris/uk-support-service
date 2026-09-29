from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

from src.core.constants import TicketStatus, TicketType
from src.repositories.ticket_repository import TicketRepository
from src.services.dashboard_service import DashboardService


def _row(**overrides) -> SimpleNamespace:
    mapping = {
        "type": TicketType.REQUEST,
        "status": TicketStatus.NEW,
        "category_id": 1,
        "category_title": "🚰 Сантехника",
        "category_sort_order": 1,
        "created_at": datetime.now(UTC) - timedelta(hours=2),
        "closed_at": None,
        "reacted_at": None,
        "rating": None,
        "building_id": 1,
        "building_address": "ул. Ленина, 12",
        "assignee_id": None,
    }
    mapping.update(overrides)
    return SimpleNamespace(_mapping=mapping)


async def _service(monkeypatch, rows: list[SimpleNamespace]) -> DashboardService:
    list_for_dashboard = AsyncMock(return_value=rows)
    monkeypatch.setattr(TicketRepository, "list_for_dashboard", list_for_dashboard)
    return DashboardService(AsyncMock())


async def test_snapshot_returns_facts_and_dashboard(monkeypatch) -> None:
    rows = [_row()]
    service = await _service(monkeypatch, rows)

    facts, dashboard = await service.snapshot(30)

    assert len(facts) == 1
    assert facts[0].created_at == rows[0]._mapping["created_at"]
    assert facts[0].category_title == "🚰 Сантехника"
    assert dashboard.period_days == 30
    assert len(dashboard.daily) == 30


async def test_get_returns_the_snapshot_dashboard(monkeypatch) -> None:
    service = await _service(monkeypatch, [_row()])

    _, dashboard = await service.snapshot(7)

    assert await service.get(7) == dashboard
