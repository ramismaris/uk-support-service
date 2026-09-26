from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Form, Path, Query, UploadFile, status
from fastapi import File as FileParam
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import StaffUser
from src.core.constants import BIGINT_MAX, TicketStatus
from src.db.session import get_db
from src.models.file import File
from src.models.status_change import StatusChange
from src.providers.factory import get_messenger_provider, get_storage_provider
from src.providers.messenger_provider import MessengerProvider
from src.providers.storage_provider import StorageProvider
from src.schemas.common import PaginatedResponse
from src.schemas.file import FileResponse
from src.schemas.message import MessageResponse
from src.schemas.ticket import (
    StatusChangeResponse,
    TicketDetailResponse,
    TicketListItemResponse,
)
from src.services.file_service import MAX_FILE_SIZE
from src.services.message_service import MessageService, UploadedFile
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
        last_client_message_at=ticket.last_client_message_at,
        staff_seen_at=ticket.staff_seen_at,
        contact_phone=ticket.contact_phone,
        preferred_time=ticket.preferred_time,
        rating=ticket.rating,
        closed_at=ticket.closed_at,
        files=_files(files),
        history=_history(history),
    )


@router.get("/tickets/{ticket_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    ticket_id: Annotated[int, Path(ge=1, le=BIGINT_MAX)],
    staff: StaffUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[MessageResponse]:
    messages = await TicketService(db).list_messages(ticket_id)
    return [MessageResponse.model_validate(message) for message in messages]


@router.post(
    "/tickets/{ticket_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    ticket_id: Annotated[int, Path(ge=1, le=BIGINT_MAX)],
    staff: StaffUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    messenger: Annotated[MessengerProvider, Depends(get_messenger_provider)],
    storage: Annotated[StorageProvider, Depends(get_storage_provider)],
    text: Annotated[str | None, Form()] = None,
    files: Annotated[list[UploadFile] | None, FileParam()] = None,
) -> MessageResponse:
    uploads = [
        UploadedFile(
            data=await upload.read(MAX_FILE_SIZE + 1),
            mime=upload.content_type or "application/octet-stream",
            filename=upload.filename,
        )
        for upload in files or []
    ]
    message = await MessageService(db, messenger, storage).send_staff_message(
        ticket_id, staff, text, uploads
    )
    return MessageResponse.model_validate(message)


@router.post("/tickets/{ticket_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(
    ticket_id: Annotated[int, Path(ge=1, le=BIGINT_MAX)],
    staff: StaffUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    await TicketService(db).mark_read(ticket_id)


def _files(files: list[File]) -> list[FileResponse]:
    return [FileResponse.model_validate(file) for file in files]


def _history(history: list[StatusChange]) -> list[StatusChangeResponse]:
    return [StatusChangeResponse.model_validate(change) for change in history]
