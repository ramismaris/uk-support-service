from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
)

from src.core.constants import BIGINT_MAX
from src.core.texts import DIRECTORY_NAME_MARKUP
from src.schemas.common import NoNul

# Names go into bot buttons next to an apartment («адрес, кв. N», apartment up to 20)
# or a ticket number («№N · категория»), and Max accepts up to 128 characters in a button
# text (checked live 2026-09-30).
DIRECTORY_NAME_LIMIT = 64

# Max markdown markers: **, *, _, ~~, ++, ^^, `, [text](url), "# " heading, "> " quote.
# The category title and the address go to the resident inside the status card, sent as markdown.
_MARKUP_CHARS = frozenset("*_~^+`[]#>")

MAX_ORDER_IDS = 1000


def _collapse_whitespace(value: object) -> object:
    if isinstance(value, str):
        return " ".join(value.split())
    return value


def _reject_markup(value: str) -> str:
    if _MARKUP_CHARS & set(value):
        raise ValueError(DIRECTORY_NAME_MARKUP)
    return value


DirectoryName = Annotated[
    str,
    BeforeValidator(_collapse_whitespace),
    StringConstraints(min_length=1, max_length=DIRECTORY_NAME_LIMIT),
    NoNul,
    AfterValidator(_reject_markup),
]

DirectoryId = Annotated[int, Field(ge=1, le=BIGINT_MAX)]


class BuildingCreateRequest(BaseModel):
    address: DirectoryName


class BuildingUpdateRequest(BaseModel):
    address: DirectoryName | None = None
    is_active: bool | None = None


class CategoryCreateRequest(BaseModel):
    title: DirectoryName


class CategoryUpdateRequest(BaseModel):
    title: DirectoryName | None = None
    is_active: bool | None = None


class CategoryOrderRequest(BaseModel):
    ids: Annotated[list[DirectoryId], Field(min_length=1, max_length=MAX_ORDER_IDS)]


class AdminBuildingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    address: str
    is_active: bool


class AdminCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    is_active: bool
