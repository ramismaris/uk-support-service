from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, computed_field

from src.core.constants import BIGINT_MAX, ContentKey
from src.core.security import build_file_url
from src.schemas.common import NoNul

CONTENT_TEXT_LIMIT = 3000

ContentText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=CONTENT_TEXT_LIMIT),
    NoNul,
]
FileId = Annotated[int, Field(ge=1, le=BIGINT_MAX)]


class ContactPhone(BaseModel):
    title: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50), NoNul
    ]
    phone: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30), NoNul
    ]


class WelcomeContent(BaseModel):
    text: ContentText
    file_id: FileId | None = None


class WelcomeContentUpdate(WelcomeContent):
    # The admin API requires the photo; a stored block may lack it until the first upload.
    file_id: FileId


class EmergencyContent(BaseModel):
    text: ContentText


class ServicesContent(BaseModel):
    text: ContentText


class PaymentContent(BaseModel):
    text: ContentText
    url: Annotated[
        str,
        StringConstraints(strip_whitespace=True, max_length=2048, pattern=r"^https?://\S+$"),
        NoNul,
    ]
    button_text: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64), NoNul
    ]


class ContactsContent(BaseModel):
    text: ContentText
    phones: Annotated[list[ContactPhone], Field(max_length=10)]


class ThemeContent(BaseModel):
    company_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100), NoNul
    ]
    primary_color: Annotated[str, StringConstraints(pattern=r"^#[0-9A-Fa-f]{6}$")]
    logo_file_id: FileId | None = None


class WelcomeContentResponse(WelcomeContent):
    @computed_field
    @property
    def file_url(self) -> str | None:
        if self.file_id is None:
            return None
        return build_file_url(self.file_id, datetime.now(UTC))


class ThemeContentResponse(ThemeContent):
    @computed_field
    @property
    def logo_url(self) -> str | None:
        if self.logo_file_id is None:
            return None
        return build_file_url(self.logo_file_id, datetime.now(UTC))


class ContentResponse(BaseModel):
    welcome: WelcomeContentResponse | None = None
    emergency: EmergencyContent | None = None
    services: ServicesContent | None = None
    payment: PaymentContent | None = None
    contacts: ContactsContent | None = None
    theme: ThemeContentResponse | None = None


CONTENT_MODELS: dict[ContentKey, type[BaseModel]] = {
    ContentKey.WELCOME: WelcomeContent,
    ContentKey.EMERGENCY: EmergencyContent,
    ContentKey.SERVICES: ServicesContent,
    ContentKey.PAYMENT: PaymentContent,
    ContentKey.CONTACTS: ContactsContent,
    ContentKey.THEME: ThemeContent,
}
