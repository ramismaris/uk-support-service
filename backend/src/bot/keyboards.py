from maxapi.types import CallbackButton, LinkButton
from maxapi.types.attachments import AttachmentButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from src.schemas.content import PaymentContent

MENU_EMERGENCY = "menu:emergency"
MENU_SERVICES = "menu:services"
MENU_PAYMENT = "menu:payment"
MENU_MAIN = "menu:main"

MENU_PREFIX = "menu:"


def main_menu_keyboard() -> AttachmentButton:
    builder = InlineKeyboardBuilder()
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
