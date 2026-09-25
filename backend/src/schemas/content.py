from pydantic import BaseModel

from src.core.constants import ContentKey


class ContactPhone(BaseModel):
    title: str
    phone: str


class WelcomeContent(BaseModel):
    text: str
    file_id: int | None = None


class EmergencyContent(BaseModel):
    text: str


class ServicesContent(BaseModel):
    text: str


class PaymentContent(BaseModel):
    text: str
    url: str
    button_text: str


class ContactsContent(BaseModel):
    text: str
    phones: list[ContactPhone]


class ThemeContent(BaseModel):
    company_name: str
    primary_color: str
    logo_file_id: int | None = None


CONTENT_MODELS: dict[ContentKey, type[BaseModel]] = {
    ContentKey.WELCOME: WelcomeContent,
    ContentKey.EMERGENCY: EmergencyContent,
    ContentKey.SERVICES: ServicesContent,
    ContentKey.PAYMENT: PaymentContent,
    ContentKey.CONTACTS: ContactsContent,
    ContentKey.THEME: ThemeContent,
}
