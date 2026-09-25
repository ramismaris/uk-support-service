from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.auth.router import router as auth_router
from src.api.v1.files.router import router as files_router
from src.api.v1.staff.router import router as staff_router
from src.db.session import get_db

router = APIRouter()
router.include_router(auth_router)
router.include_router(files_router)
router.include_router(staff_router)


@router.get("/health")
async def health(db: Annotated[AsyncSession, Depends(get_db)]) -> dict[str, str]:
    await db.execute(text("SELECT 1"))
    return {"status": "ok"}
