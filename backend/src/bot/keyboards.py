from maxapi.types import CallbackButton, LinkButton, RequestContactButton
from maxapi.types.attachments import AttachmentButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from src.core.constants import CHAT_TICKET_PREFIX
from src.core.texts import (
    CHAT_NEW_QUESTION_BUTTON,
    CHAT_NO_BUTTON,
    CHAT_YES_BUTTON,
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
    MY_TICKETS_BUTTON,
    MY_TICKETS_WRITE_BUTTON,
    QUESTION_BUTTON,
    QUESTION_WRITE_BUTTON,
    ticket_button_label,
    ticket_dative,
)
from src.schemas.content import PaymentContent
from src.services.ticket_rules import is_open

MENU_EMERGENCY = "menu:emergency"
MENU_SERVICES = "menu:services"
MENU_PAYMENT = "menu:payment"
MENU_TICKETS = "menu:tickets"
MENU_QUESTION = "menu:question"
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

CHAT_CHOOSE_PREFIX = "chat:choose:"
CHAT_QUESTION = "chat:question"
CHAT_CANCEL = "chat:cancel"

CHAT_PREFIX = "chat:"

QUESTION_WRITE = "question:write"
QUESTION_CANCEL = "question:cancel"

QUESTION_PREFIX = "question:"

RATE_PREFIX = "rate:"


def main_menu_keyboard() -> AttachmentButton:
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text=FORM_START_BUTTON, payload=FORM_START))
    builder.row(CallbackButton(text=MY_TICKETS_BUTTON, payload=MENU_TICKETS))
    builder.row(CallbackButton(text=QUESTION_BUTTON, payload=MENU_QUESTION))
    builder.row(CallbackButton(text="Аварийные службы", payload=MENU_EMERGENCY))
    builder.row(CallbackButton(text="Услуги УК", payload=MENU_SERVICES))
    builder.row(CallbackButton(text="Оплата ЖКХ", payload=MENU_PAYMENT))
    return builder.as_markup()


def my_tickets_keyboard(tickets: list) -> AttachmentButton:
    builder = InlineKeyboardBuilder()
    for ticket in tickets:
        if not is_open(ticket.status):
            continue
        label = ticket_dative(ticket.type, ticket.id)
        builder.row(
            CallbackButton(
                text=MY_TICKETS_WRITE_BUTTON.format(label=label),
                payload=f"{CHAT_TICKET_PREFIX}{ticket.id}",
            )
        )
    builder.row(CallbackButton(text="« В меню", payload=MENU_MAIN))
    return builder.as_markup()


def my_tickets_empty_keyboard() -> AttachmentButton:
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text=FORM_START_BUTTON, payload=FORM_START))
    builder.row(CallbackButton(text="« В меню", payload=MENU_MAIN))
    return builder.as_markup()


def contacts_keyboard() -> AttachmentButton:
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text=QUESTION_WRITE_BUTTON, payload=QUESTION_WRITE))
    builder.row(CallbackButton(text="« В меню", payload=MENU_MAIN))
    return builder.as_markup()


def question_cancel_keyboard() -> AttachmentButton:
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text=FORM_CANCEL_BUTTON, payload=QUESTION_CANCEL))
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


def choose_ticket_keyboard(tickets: list, *, with_question: bool) -> AttachmentButton:
    builder = InlineKeyboardBuilder()
    for ticket in tickets:
        category_title = ticket.category.title if ticket.category else None
        label = ticket_button_label(ticket.type, ticket.id, category_title)
        builder.row(CallbackButton(text=label, payload=f"{CHAT_CHOOSE_PREFIX}{ticket.id}"))
    if with_question:
        builder.row(CallbackButton(text=CHAT_NEW_QUESTION_BUTTON, payload=CHAT_QUESTION))
    builder.row(CallbackButton(text=FORM_CANCEL_BUTTON, payload=CHAT_CANCEL))
    return builder.as_markup()


def confirm_question_keyboard() -> AttachmentButton:
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text=CHAT_YES_BUTTON, payload=CHAT_QUESTION))
    builder.row(CallbackButton(text=CHAT_NO_BUTTON, payload=CHAT_CANCEL))
    return builder.as_markup()


def rating_keyboard(ticket_id: int) -> AttachmentButton:
    builder = InlineKeyboardBuilder()
    builder.row(
        *[
            CallbackButton(text=str(score), payload=f"{RATE_PREFIX}{ticket_id}:{score}")
            for score in range(1, 6)
        ]
    )
    return builder.as_markup()
