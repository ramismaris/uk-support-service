from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile, status
from fastapi import File as FileParam
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import AdminUser
from src.core.constants import ContentKey
from src.db.session import get_db
from src.providers.factory import get_storage_provider
from src.providers.storage_provider import StorageProvider
from src.schemas.content import (
    ContactsContent,
    ContentResponse,
    EmergencyContent,
    PaymentContent,
    ServicesContent,
    ThemeContent,
    ThemeContentResponse,
    WelcomeContent,
    WelcomeContentResponse,
    WelcomeContentUpdate,
)
from src.schemas.file import FileResponse
from src.services.content_service import ContentService
from src.services.file_service import MAX_FILE_SIZE, FileService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/content", response_model=ContentResponse)
async def get_content(
    admin: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ContentResponse:
    service = ContentService(db)
    return ContentResponse(
        welcome=_welcome(await service.get_welcome()),
        emergency=await service.get_emergency(),
        services=await service.get_services(),
        payment=await service.get_payment(),
        contacts=await service.get_contacts(),
        theme=_theme(await service.get_theme()),
    )


@router.put("/content/welcome", response_model=WelcomeContentResponse)
async def put_welcome(
    body: WelcomeContentUpdate,
    admin: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WelcomeContentResponse:
    await ContentService(db).save(ContentKey.WELCOME, body, admin)
    return WelcomeContentResponse(text=body.text, file_id=body.file_id)


@router.put("/content/emergency", response_model=EmergencyContent)
async def put_emergency(
    body: EmergencyContent,
    admin: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EmergencyContent:
    await ContentService(db).save(ContentKey.EMERGENCY, body, admin)
    return body


@router.put("/content/services", response_model=ServicesContent)
async def put_services(
    body: ServicesContent,
    admin: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ServicesContent:
    await ContentService(db).save(ContentKey.SERVICES, body, admin)
    return body


@router.put("/content/payment", response_model=PaymentContent)
async def put_payment(
    body: PaymentContent,
    admin: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PaymentContent:
    await ContentService(db).save(ContentKey.PAYMENT, body, admin)
    return body


@router.put("/content/contacts", response_model=ContactsContent)
async def put_contacts(
    body: ContactsContent,
    admin: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ContactsContent:
    await ContentService(db).save(ContentKey.CONTACTS, body, admin)
    return body


@router.put("/content/theme", response_model=ThemeContentResponse)
async def put_theme(
    body: ThemeContent,
    admin: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ThemeContentResponse:
    await ContentService(db).save(ContentKey.THEME, body, admin)
    return ThemeContentResponse(
        company_name=body.company_name,
        primary_color=body.primary_color,
        logo_file_id=body.logo_file_id,
    )


@router.post(
    "/content/images",
    response_model=FileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_content_image(
    admin: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    storage: Annotated[StorageProvider, Depends(get_storage_provider)],
    file: Annotated[UploadFile, FileParam()],
) -> FileResponse:
    data = await file.read(MAX_FILE_SIZE + 1)
    saved = await FileService(db, storage).save_image(data, file.filename)
    return FileResponse.model_validate(saved)


def _welcome(content: WelcomeContent | None) -> WelcomeContentResponse | None:
    if content is None:
        return None
    return WelcomeContentResponse(text=content.text, file_id=content.file_id)


def _theme(content: ThemeContent | None) -> ThemeContentResponse | None:
    if content is None:
        return None
    return ThemeContentResponse(
        company_name=content.company_name,
        primary_color=content.primary_color,
        logo_file_id=content.logo_file_id,
    )
