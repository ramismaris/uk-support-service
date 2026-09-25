from maxapi import Router
from maxapi.filters import F
from maxapi.filters.command import CommandStart
from maxapi.types import BotStarted, MessageCallback, MessageCreated
from maxapi.types.attachments import AttachmentButton
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards import (
    MENU_EMERGENCY,
    MENU_MAIN,
    MENU_PAYMENT,
    MENU_PREFIX,
    MENU_SERVICES,
    back_keyboard,
    main_menu_keyboard,
    payment_keyboard,
)
from src.core.texts import (
    OUTDATED_BUTTON_TEXT,
    SECTION_EMPTY_TEXT,
    START_TEXT,
    USE_MENU_TEXT,
)
from src.services.content_service import ContentService

router = Router("menu")


async def _welcome_text(db: AsyncSession) -> str:
    content = await ContentService(db).get_welcome()
    return content.text if content is not None else START_TEXT


async def _edit(event: MessageCallback, text: str, keyboard: AttachmentButton) -> None:
    try:
        await event.edit(text=text, attachments=[keyboard])
    except ValueError:
        await event.ack(notification=OUTDATED_BUTTON_TEXT)


@router.bot_started()
async def handle_bot_started(event: BotStarted, db: AsyncSession) -> None:
    text = await _welcome_text(db)
    await event.bot.send_message(
        chat_id=event.chat_id,
        text=text,
        attachments=[main_menu_keyboard()],
    )


@router.message_created(CommandStart())
async def handle_start(event: MessageCreated, db: AsyncSession) -> None:
    text = await _welcome_text(db)
    await event.message.answer(text, attachments=[main_menu_keyboard()])


@router.message_callback(F.callback.payload == MENU_EMERGENCY)
async def handle_emergency(event: MessageCallback, db: AsyncSession) -> None:
    content = await ContentService(db).get_emergency()
    text = content.text if content is not None else SECTION_EMPTY_TEXT
    await _edit(event, text, back_keyboard())


@router.message_callback(F.callback.payload == MENU_SERVICES)
async def handle_services(event: MessageCallback, db: AsyncSession) -> None:
    content = await ContentService(db).get_services()
    text = content.text if content is not None else SECTION_EMPTY_TEXT
    await _edit(event, text, back_keyboard())


@router.message_callback(F.callback.payload == MENU_PAYMENT)
async def handle_payment(event: MessageCallback, db: AsyncSession) -> None:
    content = await ContentService(db).get_payment()
    if content is None:
        await _edit(event, SECTION_EMPTY_TEXT, back_keyboard())
        return
    await _edit(event, content.text, payment_keyboard(content))


@router.message_callback(F.callback.payload == MENU_MAIN)
async def handle_main(event: MessageCallback, db: AsyncSession) -> None:
    text = await _welcome_text(db)
    await _edit(event, text, main_menu_keyboard())


@router.message_callback(F.callback.payload.regexp(rf"^{MENU_PREFIX}"))
async def handle_unknown_menu(event: MessageCallback) -> None:
    await event.ack(notification=OUTDATED_BUTTON_TEXT)


@router.message_created()
async def handle_free_text(event: MessageCreated) -> None:
    await event.message.answer(USE_MENU_TEXT, attachments=[main_menu_keyboard()])
