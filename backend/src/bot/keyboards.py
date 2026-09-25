from maxapi.types import CallbackButton, LinkButton, RequestContactButton
from maxapi.types.attachments import AttachmentButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from src.core.texts import (
    FORM_ADDRESS_ADD_BUTTON,
    FORM_ADDRESS_OK_BUTTON,
    FORM_ADDRESS_OTHER_BUTTON,
    FORM_CANCEL_BUTTON,
    FORM_CONTACT_BUTTON,
    FORM_PHOTOS_DONE_BUTTON,
    FORM_PHOTOS_SKIP_BUTTON,
    FORM_SEND_BUTTON,
    FORM_START_BUTTON,
    FORM_TIME_SKIP_BUTTON,
)
from src.schemas.content import PaymentContent

MENU_EMERGENCY = "menu:emergency"
MENU_SERVICES = "menu:services"
MENU_PAYMENT = "menu:payment"
MENU_MAIN = "menu:main"

MENU_PREFIX = "menu:"

FORM_START = "form:start"
FORM_CANCEL = "form:cancel"
FORM_CATEGORY_PREFIX = "form:category:"
FORM_ADDRESS_OK = "form:address:ok"
FORM_ADDRESS_OTHER = "form:address:other"
FORM_ADDRESS_ADD = "form:address:add"
FORM_RESIDENCE_PREFIX = "form:residence:"
FORM_BUILDING_PREFIX = "form:building:"
FORM_PHOTOS_SKIP = "form:photos:skip"
FORM_PHOTOS_DONE = "form:photos:done"
FORM_TIME_SKIP = "form:time:skip"
FORM_SEND = "form:send"

FORM_PREFIX = "form:"


def main_menu_keyboard() -> AttachmentButton:
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text=FORM_START_BUTTON, payload=FORM_START))
    builder.row(CallbackButton(text="Аварийные службы", payload=MENU_EMERGENCY))
    builder.row(CallbackButton(text="Услуги УК", payload=MENU_SERVICES))
    builder.row(CallbackButton(text="Оплата ЖКХ", payload=MENU_PAYMENT))
    return builder.as_markup()


def back_keyboard() -> AttachmentButton:
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="« В меню", payload=MENU_MAIN))
    return builder.as_markup()


def payment_keyboard(content: PaymentContent) -> AttachmentButton:
    builder = InlineKeyboardBuilder()
    builder.row(LinkButton(text=content.button_text, url=content.url))
    builder.row(CallbackButton(text="« В меню", payload=MENU_MAIN))
    return builder.as_markup()


def _cancel_row(builder: InlineKeyboardBuilder) -> None:
    builder.row(CallbackButton(text=FORM_CANCEL_BUTTON, payload=FORM_CANCEL))


def phone_keyboard() -> AttachmentButton:
    builder = InlineKeyboardBuilder()
    builder.row(RequestContactButton(text=FORM_CONTACT_BUTTON))
    _cancel_row(builder)
    return builder.as_markup()


def category_keyboard(categories: list) -> AttachmentButton:
    builder = InlineKeyboardBuilder()
    for category in categories:
        builder.row(
            CallbackButton(text=category.title, payload=f"{FORM_CATEGORY_PREFIX}{category.id}")
        )
    _cancel_row(builder)
    return builder.as_markup()


def address_keyboard() -> AttachmentButton:
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text=FORM_ADDRESS_OK_BUTTON, payload=FORM_ADDRESS_OK))
    builder.row(CallbackButton(text=FORM_ADDRESS_OTHER_BUTTON, payload=FORM_ADDRESS_OTHER))
    _cancel_row(builder)
    return builder.as_markup()


def residences_keyboard(options: list[tuple[int, str]]) -> AttachmentButton:
    builder = InlineKeyboardBuilder()
    for residence_id, label in options:
        builder.row(CallbackButton(text=label, payload=f"{FORM_RESIDENCE_PREFIX}{residence_id}"))
    builder.row(CallbackButton(text=FORM_ADDRESS_ADD_BUTTON, payload=FORM_ADDRESS_ADD))
    _cancel_row(builder)
    return builder.as_markup()


def building_keyboard(buildings: list) -> AttachmentButton:
    builder = InlineKeyboardBuilder()
    for building in buildings:
        builder.row(
            CallbackButton(text=building.address, payload=f"{FORM_BUILDING_PREFIX}{building.id}")
        )
    _cancel_row(builder)
    return builder.as_markup()


def cancel_keyboard() -> AttachmentButton:
    builder = InlineKeyboardBuilder()
    _cancel_row(builder)
    return builder.as_markup()


def photos_skip_keyboard() -> AttachmentButton:
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text=FORM_PHOTOS_SKIP_BUTTON, payload=FORM_PHOTOS_SKIP))
    _cancel_row(builder)
    return builder.as_markup()


def photos_done_keyboard() -> AttachmentButton:
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text=FORM_PHOTOS_DONE_BUTTON, payload=FORM_PHOTOS_DONE))
    _cancel_row(builder)
    return builder.as_markup()


def time_keyboard() -> AttachmentButton:
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text=FORM_TIME_SKIP_BUTTON, payload=FORM_TIME_SKIP))
    _cancel_row(builder)
    return builder.as_markup()


def confirm_keyboard() -> AttachmentButton:
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text=FORM_SEND_BUTTON, payload=FORM_SEND))
    _cancel_row(builder)
    return builder.as_markup()
