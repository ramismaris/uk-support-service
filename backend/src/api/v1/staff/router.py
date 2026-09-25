from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import StaffUser
from src.core.constants import BIGINT_MAX, TicketStatus
from src.db.session import get_db
from src.models.file import File
from src.models.status_change import StatusChange
from src.schemas.common import PaginatedResponse
from src.schemas.file import FileResponse
from src.schemas.ticket import (
    StatusChangeResponse,
    TicketDetailResponse,
    TicketListItemResponse,
)
from src.services.ticket_service import TicketService

router = APIRouter(prefix="/staff", tags=["staff"])

OpenStatus = Literal[
    TicketStatus.NEW,
    TicketStatus.IN_PROGRESS,
    TicketStatus.WAITING_CLIENT,
]


@router.get("/tickets", response_model=PaginatedResponse[TicketListItemResponse])
async def list_tickets(
    staff: StaffUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    status: OpenStatus | None = None,
    building_id: Annotated[int | None, Query(ge=1, le=BIGINT_MAX)] = None,
    category_id: Annotated[int | None, Query(ge=1, le=BIGINT_MAX)] = None,
    mine: bool = False,
    skip: Annotated[int, Query(ge=0, le=BIGINT_MAX)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> PaginatedResponse[TicketListItemResponse]:
    tickets, total = await TicketService(db).list_for_staff(
        staff,
        status=status,
        building_id=building_id,
        category_id=category_id,
        mine=mine,
        skip=skip,
        limit=limit,
    )
    return PaginatedResponse(
        total=total,
        items=[TicketListItemResponse.model_validate(ticket) for ticket in tickets],
    )


@router.get("/tickets/{ticket_id}", response_model=TicketDetailResponse)
async def get_ticket(
    ticket_id: Annotated[int, Path(ge=1, le=BIGINT_MAX)],
    staff: StaffUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TicketDetailResponse:
    ticket, files, history = await TicketService(db).get_for_staff(ticket_id)
    return TicketDetailResponse(
        id=ticket.id,
        type=ticket.type,
        status=ticket.status,
        priority=ticket.priority,
        description=ticket.description,
        category=ticket.category,
        building=ticket.building,
        apartment=ticket.apartment,
        client=ticket.client,
        assignee=ticket.assignee,
        created_at=ticket.created_at,
        contact_phone=ticket.contact_phone,
        preferred_time=ticket.preferred_time,
        rating=ticket.rating,
        closed_at=ticket.closed_at,
        files=_files(files),
        history=_history(history),
    )


def _files(files: list[File]) -> list[FileResponse]:
    return [FileResponse.model_validate(file) for file in files]


def _history(history: list[StatusChange]) -> list[StatusChangeResponse]:
    return [StatusChangeResponse.model_validate(change) for change in history]
