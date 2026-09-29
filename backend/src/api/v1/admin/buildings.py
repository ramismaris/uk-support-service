from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import AdminUser
from src.core.constants import BIGINT_MAX
from src.db.session import get_db
from src.schemas.directory import (
    AdminBuildingResponse,
    BuildingCreateRequest,
    BuildingUpdateRequest,
)
from src.services.building_service import BuildingService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/buildings", response_model=list[AdminBuildingResponse])
async def list_buildings(
    admin: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AdminBuildingResponse]:
    buildings = await BuildingService(db).list_all()
    return [AdminBuildingResponse.model_validate(building) for building in buildings]


@router.post(
    "/buildings",
    response_model=AdminBuildingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_building(
    body: BuildingCreateRequest,
    admin: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminBuildingResponse:
    building = await BuildingService(db).create(body.address)
    return AdminBuildingResponse.model_validate(building)


@router.patch("/buildings/{building_id}", response_model=AdminBuildingResponse)
async def update_building(
    building_id: Annotated[int, Path(ge=1, le=BIGINT_MAX)],
    body: BuildingUpdateRequest,
    admin: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminBuildingResponse:
    building = await BuildingService(db).update(
        building_id, address=body.address, is_active=body.is_active
    )
    return AdminBuildingResponse.model_validate(building)
