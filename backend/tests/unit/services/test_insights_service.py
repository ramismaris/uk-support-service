import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest

from src.core.config import settings
from src.core.constants import TicketStatus, TicketType
from src.core.exceptions import LlmException
from src.providers.llm_provider import LlmProvider
from src.repositories.user_repository import UserRepository
from src.services.dashboard import TicketFacts, build_dashboard
from src.services.dashboard_service import DashboardService
from src.services.insights import SYSTEM_PROMPT
from src.services.insights_service import InsightsCache, InsightsService

TZ = ZoneInfo(settings.timezone)
NOW = datetime.now(UTC)
REACTION = timedelta(hours=4)
RESOLUTION = timedelta(hours=72)


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


@pytest.fixture(autouse=True)
def _insights_enabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ai_insights_enabled", True)


def _answer(items: list[dict]) -> str:
    return json.dumps({"items": items})


def _fact(**overrides) -> TicketFacts:
    mapping = {
        "type": TicketType.REQUEST,
        "status": TicketStatus.NEW,
        "category_id": 1,
        "category_title": "🚰 Сантехника",
        "category_sort_order": 1,
        "created_at": NOW - timedelta(days=2),
        "closed_at": None,
        "reacted_at": None,
        "rating": None,
        "building_id": 1,
        "building_address": "ул. Ленина, 1",
        "assignee_id": 101,
    }
    mapping.update(overrides)
    return TicketFacts(**mapping)


def _dashboard(facts: list[TicketFacts]):
    return build_dashboard(facts, now=NOW, days=30, tz=TZ, reaction=REACTION, resolution=RESOLUTION)


def _patch(monkeypatch, facts: list[TicketFacts], users: list | None = None):
    dashboard = _dashboard(facts)
    snapshot = AsyncMock(return_value=(facts, dashboard))
    monkeypatch.setattr(DashboardService, "snapshot", snapshot)
    list_by_ids = AsyncMock(return_value=users or [])
    monkeypatch.setattr(UserRepository, "list_by_ids", list_by_ids)
    return snapshot, list_by_ids


def _llm(answer: str) -> AsyncMock:
    provider = AsyncMock(spec=LlmProvider)
    provider.complete_json = AsyncMock(return_value=answer)
    return provider


def _service(provider, cache: InsightsCache) -> tuple[InsightsService, AsyncMock]:
    db = AsyncMock()
    return InsightsService(db, provider, cache), db


async def test_disabled_when_no_llm(monkeypatch) -> None:
    snapshot, list_by_ids = _patch(monkeypatch, [_fact()])
    cache = InsightsCache(clock=FakeClock())
    service, db = _service(None, cache)

    response = await service.get(30)

    assert response.status == "disabled"
    assert response.period_days == 30
    assert response.generated_at is None
    assert response.items == []
    snapshot.assert_not_awaited()
    list_by_ids.assert_not_awaited()
    db.commit.assert_not_awaited()
    assert cache.get(30) is None


async def test_disabled_when_flag_off(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ai_insights_enabled", False)
    snapshot, list_by_ids = _patch(monkeypatch, [_fact()])
    provider = _llm(_answer([{"kind": "fact", "text": "Вывод 1."}]))
    cache = InsightsCache(clock=FakeClock())
    service, db = _service(provider, cache)

    response = await service.get(30)

    assert response.status == "disabled"
    assert response.items == []
    provider.complete_json.assert_not_awaited()
    snapshot.assert_not_awaited()
    list_by_ids.assert_not_awaited()
    db.commit.assert_not_awaited()


async def test_success_substitutes_manager_name(monkeypatch) -> None:
    facts = [_fact()]
    users = [SimpleNamespace(id=101, first_name="Пётр", last_name="Смирнов")]
    _patch(monkeypatch, facts, users)
    provider = _llm(_answer([{"kind": "fact", "text": "[[m1]] закрыл 10 заявок."}]))
    cache = InsightsCache(clock=FakeClock())
    service, _ = _service(provider, cache)

    response = await service.get(30)

    assert response.status == "ok"
    assert response.period_days == 30
    assert response.generated_at is not None
    assert [item.kind for item in response.items] == ["fact"]
    assert [item.text for item in response.items] == ["Пётр Смирнов закрыл 10 заявок."]
    provider.complete_json.assert_awaited_once()
    system, user = provider.complete_json.call_args.args
    assert system == SYSTEM_PROMPT
    data = json.loads(user)
    assert data["period_days"] == 30
    assert set(data) == {
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


async def test_prompt_has_no_manager_name_or_id(monkeypatch) -> None:
    facts = [_fact(assignee_id=424242)]
    users = [SimpleNamespace(id=424242, first_name="Пётр", last_name="Секретный")]
    _patch(monkeypatch, facts, users)
    provider = _llm(_answer([{"kind": "fact", "text": "[[m1]] закрыл 10 заявок."}]))
    service, _ = _service(provider, InsightsCache(clock=FakeClock()))

    await service.get(30)

    prompt = provider.complete_json.call_args.args[1]
    assert "Пётр" not in prompt
    assert "Секретный" not in prompt
    assert "424242" not in prompt
    assert "assignee_id" not in prompt


async def test_cache_serves_within_ttl(monkeypatch) -> None:
    _patch(monkeypatch, [_fact()], [SimpleNamespace(id=101, first_name="Пётр", last_name=None)])
    provider = _llm(_answer([{"kind": "fact", "text": "[[m1]] закрыл 10 заявок."}]))
    clock = FakeClock()
    service, _ = _service(provider, InsightsCache(clock=clock))

    first = await service.get(30)
    second = await service.get(30)

    assert first is second
    provider.complete_json.assert_awaited_once()


async def test_cache_expires_after_success_ttl(monkeypatch) -> None:
    _patch(monkeypatch, [_fact()], [SimpleNamespace(id=101, first_name="Пётр", last_name=None)])
    provider = _llm(_answer([{"kind": "fact", "text": "[[m1]] закрыл 10 заявок."}]))
    clock = FakeClock()
    service, _ = _service(provider, InsightsCache(clock=clock))

    await service.get(30)
    clock.advance(3600)
    await service.get(30)

    assert provider.complete_json.await_count == 2


async def test_refresh_bypasses_cache_and_replaces_entry(monkeypatch) -> None:
    _patch(monkeypatch, [_fact()], [SimpleNamespace(id=101, first_name="Пётр", last_name=None)])
    provider = _llm(_answer([{"kind": "fact", "text": "Первый вывод 10."}]))
    service, _ = _service(provider, InsightsCache(clock=FakeClock()))

    await service.get(30)
    provider.complete_json.return_value = _answer(
        [{"kind": "observation", "text": "Второй вывод 20."}]
    )
    refreshed = await service.get(30, refresh=True)
    cached = await service.get(30)

    assert provider.complete_json.await_count == 2
    assert refreshed.items[0].text == "Второй вывод 20."
    assert cached == refreshed


async def test_different_periods_have_separate_entries(monkeypatch) -> None:
    _patch(monkeypatch, [_fact()], [SimpleNamespace(id=101, first_name="Пётр", last_name=None)])
    provider = _llm(_answer([{"kind": "fact", "text": "[[m1]] закрыл 10 заявок."}]))
    service, _ = _service(provider, InsightsCache(clock=FakeClock()))

    await service.get(7)
    await service.get(30)
    await service.get(7)

    assert provider.complete_json.await_count == 2


async def test_failure_is_cached_for_failure_ttl(monkeypatch) -> None:
    _patch(monkeypatch, [_fact()])
    provider = _llm("")
    provider.complete_json.side_effect = LlmException()
    clock = FakeClock()
    service, _ = _service(provider, InsightsCache(clock=clock))

    first = await service.get(30)
    second = await service.get(30)
    clock.advance(300)
    third = await service.get(30)

    assert first.status == "unavailable"
    assert first.generated_at is None
    assert first.items == []
    assert second == first
    assert provider.complete_json.await_count == 2
    assert third.status == "unavailable"


async def test_unparsable_answer_is_unavailable(monkeypatch) -> None:
    _patch(monkeypatch, [_fact()])
    provider = _llm("не JSON вовсе")
    service, _ = _service(provider, InsightsCache(clock=FakeClock()))

    response = await service.get(30)

    assert response.status == "unavailable"
    assert response.items == []


async def test_failed_refresh_keeps_earlier_good_entry(monkeypatch) -> None:
    _patch(monkeypatch, [_fact()], [SimpleNamespace(id=101, first_name="Пётр", last_name=None)])
    provider = _llm(_answer([{"kind": "fact", "text": "Хороший вывод 10."}]))
    service, _ = _service(provider, InsightsCache(clock=FakeClock()))

    good = await service.get(30)
    provider.complete_json.side_effect = LlmException()
    failed = await service.get(30, refresh=True)
    cached = await service.get(30)

    assert good.status == "ok"
    assert failed.status == "unavailable"
    assert cached == good


async def test_empty_facts_returns_ok_without_llm(monkeypatch) -> None:
    _patch(monkeypatch, [])
    provider = _llm(_answer([{"kind": "fact", "text": "Вывод 1."}]))
    service, _ = _service(provider, InsightsCache(clock=FakeClock()))

    response = await service.get(30)
    provider.complete_json.side_effect = LlmException()
    cached = await service.get(30)

    assert response.status == "ok"
    assert response.items == []
    assert response.generated_at is not None
    assert cached.status == "ok"
    assert provider.complete_json.await_count == 0


async def test_commit_happens_before_llm_call(monkeypatch) -> None:
    order: list[str] = []
    facts = [_fact()]
    dashboard = _dashboard(facts)
    users = [SimpleNamespace(id=101, first_name="Пётр", last_name=None)]

    async def record_snapshot(self, days):
        order.append("snapshot")
        return facts, dashboard

    async def record_names(self, ids):
        order.append("names")
        return users

    monkeypatch.setattr(DashboardService, "snapshot", record_snapshot)
    monkeypatch.setattr(UserRepository, "list_by_ids", record_names)

    db = AsyncMock()

    async def record_commit() -> None:
        order.append("commit")

    db.commit = AsyncMock(side_effect=record_commit)

    async def record_llm(system: str, user: str) -> str:
        order.append("llm")
        return _answer([{"kind": "fact", "text": "[[m1]] закрыл 10 заявок."}])

    provider = AsyncMock(spec=LlmProvider)
    provider.complete_json = AsyncMock(side_effect=record_llm)

    await InsightsService(db, provider, InsightsCache(clock=FakeClock())).get(30)

    assert order == ["snapshot", "names", "commit", "llm"]


async def test_failure_log_contains_only_exception_class(monkeypatch, caplog) -> None:
    _patch(monkeypatch, [_fact()], [SimpleNamespace(id=101, first_name="Пётр", last_name=None)])
    secret_answer = "СЕКРЕТНЫЙ ОТВЕТ МОДЕЛИ"
    provider = _llm(secret_answer)
    service, _ = _service(provider, InsightsCache(clock=FakeClock()))

    with caplog.at_level(logging.WARNING):
        response = await service.get(30)

    assert response.status == "unavailable"
    assert "InsightsParseError" in caplog.text
    assert secret_answer not in caplog.text
    assert "Пётр" not in caplog.text
    prompt = provider.complete_json.call_args.args[1]
    assert prompt not in caplog.text


class BlockingLlm(LlmProvider):
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.calls = 0

    async def complete_json(self, system: str, user: str) -> str:
        self.calls += 1
        self.started.set()
        await self.release.wait()
        return _answer([{"kind": "fact", "text": "Вывод 10."}])


async def test_concurrent_calls_make_one_llm_request(monkeypatch) -> None:
    _patch(monkeypatch, [_fact()])
    provider = BlockingLlm()
    cache = InsightsCache(clock=FakeClock())
    service_one, _ = _service(provider, cache)
    service_two, _ = _service(provider, cache)

    first = asyncio.create_task(service_one.get(30))
    await asyncio.wait_for(provider.started.wait(), timeout=1)
    second = asyncio.create_task(service_two.get(30))
    await asyncio.sleep(0)
    provider.release.set()
    first_response, second_response = await asyncio.gather(first, second)

    assert provider.calls == 1
    assert first_response == second_response
    assert first_response.status == "ok"
