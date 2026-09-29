from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BeforeValidator
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import AdminUser
from src.db.session import get_db
from src.schemas.dashboard import DashboardResponse
from src.services.dashboard_service import DashboardService

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
