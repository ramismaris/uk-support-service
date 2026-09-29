from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import AdminUser
from src.core.constants import BIGINT_MAX
from src.db.session import get_db
from src.schemas.directory import (
    AdminCategoryResponse,
    CategoryCreateRequest,
    CategoryOrderRequest,
    CategoryUpdateRequest,
)
from src.services.category_service import CategoryService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/categories", response_model=list[AdminCategoryResponse])
async def list_categories(
    admin: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AdminCategoryResponse]:
    categories = await CategoryService(db).list_all()
    return [AdminCategoryResponse.model_validate(category) for category in categories]


@router.post(
    "/categories",
    response_model=AdminCategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_category(
    body: CategoryCreateRequest,
    admin: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminCategoryResponse:
    category = await CategoryService(db).create(body.title)
    return AdminCategoryResponse.model_validate(category)


@router.put("/categories/order", response_model=list[AdminCategoryResponse])
async def reorder_categories(
    body: CategoryOrderRequest,
    admin: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AdminCategoryResponse]:
    categories = await CategoryService(db).reorder(body.ids)
    return [AdminCategoryResponse.model_validate(category) for category in categories]


@router.patch("/categories/{category_id}", response_model=AdminCategoryResponse)
async def update_category(
    category_id: Annotated[int, Path(ge=1, le=BIGINT_MAX)],
    body: CategoryUpdateRequest,
    admin: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminCategoryResponse:
    category = await CategoryService(db).update(
        category_id, title=body.title, is_active=body.is_active
    )
    return AdminCategoryResponse.model_validate(category)
