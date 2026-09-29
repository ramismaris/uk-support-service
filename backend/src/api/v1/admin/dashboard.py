from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BeforeValidator
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import AdminUser
from src.db.session import get_db
from src.providers.factory import get_llm_provider
from src.providers.llm_provider import LlmProvider
from src.schemas.dashboard import DashboardResponse
from src.schemas.insights import InsightsResponse
from src.services.dashboard_service import DashboardService
from src.services.insights_service import InsightsService

# Literal[int] does not coerce a raw query string, so parse it before the check.
Period = Annotated[Literal[7, 30, 90], BeforeValidator(int)]

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    admin: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    period: Annotated[Period, Query()] = 30,
) -> DashboardResponse:
    return await DashboardService(db).get(period)


@router.get("/dashboard/insights", response_model=InsightsResponse)
async def get_insights(
    admin: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    llm: Annotated[LlmProvider | None, Depends(get_llm_provider)],
    period: Annotated[Period, Query()] = 30,
) -> InsightsResponse:
    return await InsightsService(db, llm).get(period)


@router.post("/dashboard/insights", response_model=InsightsResponse)
async def refresh_insights(
    admin: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    llm: Annotated[LlmProvider | None, Depends(get_llm_provider)],
    period: Annotated[Period, Query()] = 30,
) -> InsightsResponse:
    return await InsightsService(db, llm).get(period, refresh=True)
