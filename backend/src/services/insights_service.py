import asyncio
import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.exceptions import LlmException
from src.providers.llm_provider import LlmProvider
from src.repositories.user_repository import UserRepository
from src.schemas.insights import InsightItem, InsightsResponse
from src.services.dashboard_service import DashboardService
from src.services.insight_payload import build_insight_payload
from src.services.insights import (
    SYSTEM_PROMPT,
    InsightsParseError,
    build_user_prompt,
    parse_answer,
)

logger = logging.getLogger(__name__)

INSIGHTS_TTL_SECONDS = 3600
FAILURE_TTL_SECONDS = 300


class InsightsCache:
    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._entries: dict[int, tuple[float, InsightsResponse]] = {}
        self._locks: dict[int, asyncio.Lock] = {}

    def get(self, days: int) -> InsightsResponse | None:
        entry = self._entries.get(days)
        if entry is None:
            return None
        expires_at, response = entry
        if self._clock() >= expires_at:
            del self._entries[days]
            return None
        return response

    def put(self, days: int, response: InsightsResponse, ttl_seconds: float) -> None:
        self._entries[days] = (self._clock() + ttl_seconds, response)

    def lock(self, days: int) -> asyncio.Lock:
        lock = self._locks.get(days)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[days] = lock
        return lock

    def clear(self) -> None:
        self._entries.clear()
        self._locks.clear()


insights_cache = InsightsCache()


class InsightsService:
    def __init__(
        self,
        db: AsyncSession,
        llm: LlmProvider | None,
        cache: InsightsCache = insights_cache,
    ):
        self.db = db
        self.llm = llm
        self.cache = cache

    async def get(self, days: int, *, refresh: bool = False) -> InsightsResponse:
        if not settings.ai_insights_enabled or self.llm is None:
            return _response("disabled", days)

        if not refresh:
            cached = self.cache.get(days)
            if cached is not None:
                return cached

        async with self.cache.lock(days):
            if not refresh:
                cached = self.cache.get(days)
                if cached is not None:
                    return cached
            return await self._generate(days, refresh=refresh)

    async def _generate(self, days: int, *, refresh: bool) -> InsightsResponse:
        facts, dashboard = await DashboardService(self.db).snapshot(days)
        if not facts:
            response = _response("ok", days, generated_at=datetime.now(UTC))
            self.cache.put(days, response, INSIGHTS_TTL_SECONDS)
            return response

        now = datetime.now(UTC)
        payload = build_insight_payload(
            facts,
            dashboard,
            now=now,
            days=days,
            tz=ZoneInfo(settings.timezone),
            reaction=timedelta(hours=settings.sla_reaction_hours),
            resolution=timedelta(hours=settings.sla_resolution_hours),
        )
        names = await self._names(payload.manager_refs)

        # End the read transaction before the slow LLM call.
        await self.db.commit()

        try:
            raw = await self.llm.complete_json(SYSTEM_PROMPT, build_user_prompt(payload.data))
            items = parse_answer(raw, names)
        except (LlmException, InsightsParseError) as exc:
            logger.warning("AI insights request failed: %s", type(exc).__name__)
            response = _response("unavailable", days)
            if not refresh:
                self.cache.put(days, response, FAILURE_TTL_SECONDS)
            return response

        response = _response("ok", days, generated_at=datetime.now(UTC), items=items)
        self.cache.put(days, response, INSIGHTS_TTL_SECONDS)
        return response

    async def _names(self, manager_refs: dict[str, int]) -> dict[str, str]:
        users = await UserRepository(self.db).list_by_ids(manager_refs.values())
        by_id = {user.id: _display_name(user.first_name, user.last_name) for user in users}
        return {
            label: by_id[user_id] for label, user_id in manager_refs.items() if user_id in by_id
        }


def _display_name(first_name: str, last_name: str | None) -> str:
    return " ".join(f"{first_name} {last_name or ''}".split())


def _response(
    status: Literal["ok", "disabled", "unavailable"],
    days: int,
    *,
    generated_at: datetime | None = None,
    items: list[InsightItem] | None = None,
) -> InsightsResponse:
    return InsightsResponse(
        status=status,
        period_days=days,
        generated_at=generated_at,
        items=items or [],
    )
