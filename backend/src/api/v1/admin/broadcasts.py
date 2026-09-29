from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import AdminUser
from src.core.constants import BIGINT_MAX
from src.db.session import get_db
from src.providers.factory import get_messenger_provider, get_storage_provider
from src.providers.messenger_provider import MessengerProvider
from src.providers.storage_provider import StorageProvider
from src.schemas.broadcast import (
    BUILDING_IDS_MAX,
    AudienceResponse,
    BroadcastCreateRequest,
    BroadcastResponse,
    BuildingId,
)
from src.schemas.common import PaginatedResponse
from src.services.broadcast_service import BroadcastService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/broadcasts/audience", response_model=AudienceResponse)
async def get_broadcast_audience(
    admin: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    messenger: Annotated[MessengerProvider, Depends(get_messenger_provider)],
    storage: Annotated[StorageProvider, Depends(get_storage_provider)],
    building_id: Annotated[list[BuildingId] | None, Query(max_length=BUILDING_IDS_MAX)] = None,
) -> AudienceResponse:
    count = await BroadcastService(db, messenger, storage).count_audience(building_id)
    return AudienceResponse(count=count)


@router.post(
    "/broadcasts",
    response_model=BroadcastResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_broadcast(
    body: BroadcastCreateRequest,
    admin: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    messenger: Annotated[MessengerProvider, Depends(get_messenger_provider)],
    storage: Annotated[StorageProvider, Depends(get_storage_provider)],
) -> BroadcastResponse:
    broadcast = await BroadcastService(db, messenger, storage).create(
        admin, body.text, body.file_id, body.building_ids
    )
    return BroadcastResponse.model_validate(broadcast)


@router.get("/broadcasts", response_model=PaginatedResponse[BroadcastResponse])
async def list_broadcasts(
    admin: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    messenger: Annotated[MessengerProvider, Depends(get_messenger_provider)],
    storage: Annotated[StorageProvider, Depends(get_storage_provider)],
    skip: Annotated[int, Query(ge=0, le=BIGINT_MAX)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> PaginatedResponse[BroadcastResponse]:
    broadcasts, total = await BroadcastService(db, messenger, storage).list_for_admin(skip, limit)
    return PaginatedResponse(
        total=total,
        items=[BroadcastResponse.model_validate(broadcast) for broadcast in broadcasts],
    )
