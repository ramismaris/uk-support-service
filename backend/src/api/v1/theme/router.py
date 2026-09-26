from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import CurrentUser
from src.core.exceptions import NotFoundException
from src.core.texts import THEME_NOT_SET
from src.db.session import get_db
from src.schemas.content import ThemeContentResponse
from src.services.content_service import ContentService

router = APIRouter(tags=["theme"])


@router.get("/theme", response_model=ThemeContentResponse)
async def get_theme(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ThemeContentResponse:
    theme = await ContentService(db).get_theme()
    if theme is None:
        raise NotFoundException(THEME_NOT_SET)
    return ThemeContentResponse(
        company_name=theme.company_name,
        primary_color=theme.primary_color,
        logo_file_id=theme.logo_file_id,
    )
