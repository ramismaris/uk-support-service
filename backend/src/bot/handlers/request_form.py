from maxapi import Router
from maxapi.context import BaseContext
from maxapi.enums.attachment import AttachmentType
from maxapi.filters import F
from maxapi.types import MessageCallback, MessageCreated
from maxapi.types.attachments import AttachmentButton
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards import (
    FORM_ADDRESS_ADD,
    FORM_ADDRESS_OK,
    FORM_ADDRESS_OTHER,
    FORM_BUILDING_PREFIX,
    FORM_CANCEL,
    FORM_CATEGORY_PREFIX,
    FORM_PHOTOS_DONE,
    FORM_PHOTOS_SKIP,
    FORM_PREFIX,
    FORM_RESIDENCE_PREFIX,
    FORM_SEND,
    FORM_START,
    FORM_TIME_SKIP,
    address_keyboard,
    building_keyboard,
    cancel_keyboard,
    category_keyboard,
    confirm_keyboard,
    main_menu_keyboard,
    phone_keyboard,
    photos_done_keyboard,
    photos_skip_keyboard,
    residences_keyboard,
    time_keyboard,
)
from src.bot.states import RequestForm
from src.bot.utils import NOT_A_COMMAND, attachments, image_urls, message_text, parse_id
from src.core.exceptions import AppException, NotFoundException
from src.core.texts import (
    FORM_ADDRESS_OTHER_PROMPT,
    FORM_ADDRESS_PROMPT,
    FORM_APARTMENT_PROMPT,
    FORM_BUILDING_PROMPT,
    FORM_CANCELLED,
    FORM_CATEGORY_PROMPT,
    FORM_CONFIRM_PROMPT,
    FORM_DESCRIPTION_PROMPT,
    FORM_PHONE_OWN_TEXT,
    FORM_PHONE_PROMPT,
    FORM_PHOTO_FAILED,
    FORM_PHOTOS_ADDED,
    FORM_PHOTOS_LIMIT,
    FORM_PHOTOS_MAX,
    FORM_PHOTOS_PROMPT,
    FORM_SENT,
    FORM_TIME_NOT_SET,
    FORM_TIME_PROMPT,
    OUTDATED_BUTTON_TEXT,
    format_address,
)
from src.models.user import User
from src.providers.factory import get_messenger_provider, get_storage_provider
from src.services.client_ticket_service import ClientTicketService, validate_description

router = Router("request_form")


def _service(db: AsyncSession) -> ClientTicketService:
    return ClientTicketService(db, get_messenger_provider(), get_storage_provider())


def _contact(message):
    for attachment in attachments(message):
        if attachment.type == AttachmentType.CONTACT:
            return attachment
    return None


def _is_own_contact(contact, user: User) -> bool:
    max_info = getattr(contact.payload, "max_info", None)
    return max_info is not None and max_info.user_id == user.max_user_id


def _contact_phone(contact) -> str | None:
    vcf = getattr(contact.payload, "vcf", None)
    return vcf.phone if vcf is not None else None


def _primary_residence(residences: list):
    for residence in residences:
        if residence.is_primary:
            return residence
    return residences[0]


def _building_address(buildings: list, building_id: int | None) -> str:
    for building in buildings:
        if building.id == building_id:
            return building.address
    return ""


def _residence_label(buildings: list, residence) -> str:
    address = _building_address(buildings, residence.building_id)
    if address:
        return format_address(address, residence.apartment)
    return residence.apartment


async def _edit(event: MessageCallback, text: str, keyboard: AttachmentButton | None = None):
    try:
        await event.edit(text=text, attachments=[keyboard] if keyboard is not None else [])
    except ValueError:
        await event.ack(notification=OUTDATED_BUTTON_TEXT)


async def _render(
    event: MessageCreated | MessageCallback,
    context: BaseContext,
    state,
    text: str,
    keyboard: AttachmentButton,
) -> None:
    await context.set_state(state)
    if isinstance(event, MessageCallback):
        await _edit(event, text, keyboard)
    else:
        await event.message.answer(text, attachments=[keyboard])


async def _ask_category(
    event: MessageCreated | MessageCallback, context: BaseContext, service: ClientTicketService
) -> None:
    categories = await service.list_categories()
    await _render(
        event, context, RequestForm.category, FORM_CATEGORY_PROMPT, category_keyboard(categories)
    )


async def _ask_address(
    event: MessageCreated | MessageCallback,
    context: BaseContext,
    user: User,
    service: ClientTicketService,
) -> None:
    residences = await service.list_residences(user)
    if not residences:
        await _ask_building(event, context, service)
        return
    buildings = await service.list_buildings()
    primary = _primary_residence(residences)
    text = FORM_ADDRESS_PROMPT.format(address=_residence_label(buildings, primary))
    await _render(event, context, RequestForm.address, text, address_keyboard())


async def _ask_address_other(
    event: MessageCallback, context: BaseContext, user: User, service: ClientTicketService
) -> None:
    residences = await service.list_residences(user)
    buildings = await service.list_buildings()
    primary = _primary_residence(residences)
    options = [
        (residence.id, _residence_label(buildings, residence))
        for residence in residences
        if residence.id != primary.id
    ]
    await _render(
        event,
        context,
        RequestForm.address,
        FORM_ADDRESS_OTHER_PROMPT,
        residences_keyboard(options),
    )


async def _ask_building(
    event: MessageCreated | MessageCallback, context: BaseContext, service: ClientTicketService
) -> None:
    buildings = await service.list_buildings()
    await _render(
        event, context, RequestForm.building, FORM_BUILDING_PROMPT, building_keyboard(buildings)
    )


async def _ask_apartment(event: MessageCreated | MessageCallback, context: BaseContext) -> None:
    await _render(event, context, RequestForm.apartment, FORM_APARTMENT_PROMPT, cancel_keyboard())


async def _ask_description(event: MessageCreated | MessageCallback, context: BaseContext) -> None:
    await _render(
        event, context, RequestForm.description, FORM_DESCRIPTION_PROMPT, cancel_keyboard()
    )


def _photos_keyboard(photo_ids: list) -> AttachmentButton:
    return photos_done_keyboard() if photo_ids else photos_skip_keyboard()


async def _ask_photos(event: MessageCreated | MessageCallback, context: BaseContext) -> None:
    await _render(event, context, RequestForm.photos, FORM_PHOTOS_PROMPT, photos_skip_keyboard())


async def _ask_time(event: MessageCreated | MessageCallback, context: BaseContext) -> None:
    await _render(event, context, RequestForm.preferred_time, FORM_TIME_PROMPT, time_keyboard())


async def _ask_confirm(
    event: MessageCreated | MessageCallback,
    context: BaseContext,
    service: ClientTicketService,
) -> None:
    data = await context.get_data()
    categories = await service.list_categories()
    buildings = await service.list_buildings()
    category_title = next(
        (category.title for category in categories if category.id == data.get("category_id")),
        "—",
    )
    address = _building_address(buildings, data.get("building_id"))
    apartment = data.get("apartment", "")
    address_text = format_address(address, apartment) if address else apartment
    text = FORM_CONFIRM_PROMPT.format(
        category=category_title,
        address=address_text,
        description=data.get("description", ""),
        photos=len(data.get("photo_ids", [])),
        time=data.get("preferred_time") or FORM_TIME_NOT_SET,
    )
    await _render(event, context, RequestForm.confirm, text, confirm_keyboard())


@router.message_callback(F.callback.payload == FORM_START)
async def handle_form_start(
    event: MessageCallback, context: BaseContext, db: AsyncSession, user: User
) -> None:
    await context.clear()
    service = _service(db)
    if not user.phone:
        await _render(event, context, RequestForm.phone, FORM_PHONE_PROMPT, phone_keyboard())
        return
    await _ask_category(event, context, service)


@router.message_callback(F.callback.payload == FORM_CANCEL, RequestForm)
async def handle_form_cancel(
    event: MessageCallback, context: BaseContext, db: AsyncSession, user: User
) -> None:
    await context.clear()
    await _edit(event, FORM_CANCELLED, main_menu_keyboard())


@router.message_created(RequestForm.phone, NOT_A_COMMAND)
async def handle_phone(
    event: MessageCreated, context: BaseContext, db: AsyncSession, user: User
) -> None:
    contact = _contact(event.message)
    if contact is None:
        await event.message.answer(FORM_PHONE_PROMPT, attachments=[phone_keyboard()])
        return
    if not _is_own_contact(contact, user):
        await event.message.answer(FORM_PHONE_OWN_TEXT, attachments=[phone_keyboard()])
        return
    phone = _contact_phone(contact)
    if phone is None:
        await event.message.answer(FORM_PHONE_PROMPT, attachments=[phone_keyboard()])
        return
    service = _service(db)
    try:
        await service.set_phone(user, phone)
    except AppException as exc:
        await event.message.answer(exc.message, attachments=[phone_keyboard()])
        return
    await _ask_category(event, context, service)


@router.message_callback(
    F.callback.payload.regexp(rf"^{FORM_CATEGORY_PREFIX}"), RequestForm.category
)
async def handle_category(
    event: MessageCallback, context: BaseContext, db: AsyncSession, user: User
) -> None:
    category_id = parse_id(event.callback.payload, FORM_CATEGORY_PREFIX)
    service = _service(db)
    categories = await service.list_categories()
    if category_id is None or not any(category.id == category_id for category in categories):
        await event.ack(notification=OUTDATED_BUTTON_TEXT)
        return
    await context.update_data(category_id=category_id)
    await _ask_address(event, context, user, service)


@router.message_callback(F.callback.payload == FORM_ADDRESS_OK, RequestForm.address)
async def handle_address_ok(
    event: MessageCallback, context: BaseContext, db: AsyncSession, user: User
) -> None:
    residences = await _service(db).list_residences(user)
    primary = _primary_residence(residences)
    await context.update_data(building_id=primary.building_id, apartment=primary.apartment)
    await _ask_description(event, context)


@router.message_callback(F.callback.payload == FORM_ADDRESS_OTHER, RequestForm.address)
async def handle_address_other(
    event: MessageCallback, context: BaseContext, db: AsyncSession, user: User
) -> None:
    await _ask_address_other(event, context, user, _service(db))


@router.message_callback(F.callback.payload == FORM_ADDRESS_ADD, RequestForm.address)
async def handle_address_add(
    event: MessageCallback, context: BaseContext, db: AsyncSession, user: User
) -> None:
    await _ask_building(event, context, _service(db))


@router.message_callback(
    F.callback.payload.regexp(rf"^{FORM_RESIDENCE_PREFIX}"), RequestForm.address
)
async def handle_residence(
    event: MessageCallback, context: BaseContext, db: AsyncSession, user: User
) -> None:
    residence_id = parse_id(event.callback.payload, FORM_RESIDENCE_PREFIX)
    if residence_id is None:
        await event.ack(notification=OUTDATED_BUTTON_TEXT)
        return
    try:
        residence = await _service(db).get_residence(user, residence_id)
    except NotFoundException:
        await event.ack(notification=OUTDATED_BUTTON_TEXT)
        return
    await context.update_data(building_id=residence.building_id, apartment=residence.apartment)
    await _ask_description(event, context)


@router.message_callback(
    F.callback.payload.regexp(rf"^{FORM_BUILDING_PREFIX}"), RequestForm.building
)
async def handle_building(
    event: MessageCallback, context: BaseContext, db: AsyncSession, user: User
) -> None:
    building_id = parse_id(event.callback.payload, FORM_BUILDING_PREFIX)
    service = _service(db)
    buildings = await service.list_buildings()
    if building_id is None or not any(building.id == building_id for building in buildings):
        await event.ack(notification=OUTDATED_BUTTON_TEXT)
        return
    await context.update_data(building_id=building_id)
    await _ask_apartment(event, context)


@router.message_created(RequestForm.apartment, NOT_A_COMMAND)
async def handle_apartment(
    event: MessageCreated, context: BaseContext, db: AsyncSession, user: User
) -> None:
    service = _service(db)
    building_id = (await context.get_data()).get("building_id")
    if building_id is None:
        await _ask_building(event, context, service)
        return
    try:
        residence = await service.add_residence(user, building_id, message_text(event.message))
    except NotFoundException:
        await _ask_building(event, context, service)
        return
    except AppException as exc:
        await event.message.answer(exc.message, attachments=[cancel_keyboard()])
        return
    await context.update_data(building_id=residence.building_id, apartment=residence.apartment)
    await _ask_description(event, context)


@router.message_created(RequestForm.description, NOT_A_COMMAND)
async def handle_description(
    event: MessageCreated, context: BaseContext, db: AsyncSession, user: User
) -> None:
    try:
        description = validate_description(message_text(event.message))
    except AppException as exc:
        await event.message.answer(exc.message, attachments=[cancel_keyboard()])
        return
    await context.update_data(description=description)
    await _ask_photos(event, context)


@router.message_created(RequestForm.photos, NOT_A_COMMAND)
async def handle_photos(
    event: MessageCreated, context: BaseContext, db: AsyncSession, user: User
) -> None:
    photo_ids = list((await context.get_data()).get("photo_ids", []))
    urls = image_urls(event.message)
    if not urls:
        await event.message.answer(FORM_PHOTOS_PROMPT, attachments=[_photos_keyboard(photo_ids)])
        return

    service = _service(db)
    failed = False
    limit_hit = False
    for url in urls:
        if len(photo_ids) >= FORM_PHOTOS_MAX:
            limit_hit = True
            break
        try:
            photo = await service.save_photo(url)
        except AppException:
            failed = True
            continue
        photo_ids.append(photo.id)

    await context.update_data(photo_ids=photo_ids)

    if limit_hit:
        text = FORM_PHOTOS_LIMIT.format(max=FORM_PHOTOS_MAX, count=len(photo_ids))
    elif failed:
        text = FORM_PHOTO_FAILED.format(count=len(photo_ids))
    else:
        text = FORM_PHOTOS_ADDED.format(count=len(photo_ids))
    await event.message.answer(text, attachments=[_photos_keyboard(photo_ids)])


@router.message_callback(F.callback.payload == FORM_PHOTOS_DONE, RequestForm.photos)
async def handle_photos_done(
    event: MessageCallback, context: BaseContext, db: AsyncSession, user: User
) -> None:
    await _ask_time(event, context)


@router.message_callback(F.callback.payload == FORM_PHOTOS_SKIP, RequestForm.photos)
async def handle_photos_skip(
    event: MessageCallback, context: BaseContext, db: AsyncSession, user: User
) -> None:
    await _ask_time(event, context)


@router.message_created(RequestForm.preferred_time, NOT_A_COMMAND)
async def handle_time(
    event: MessageCreated, context: BaseContext, db: AsyncSession, user: User
) -> None:
    await context.update_data(preferred_time=message_text(event.message) or None)
    await _ask_confirm(event, context, _service(db))


@router.message_callback(F.callback.payload == FORM_TIME_SKIP, RequestForm.preferred_time)
async def handle_time_skip(
    event: MessageCallback, context: BaseContext, db: AsyncSession, user: User
) -> None:
    await context.update_data(preferred_time=None)
    await _ask_confirm(event, context, _service(db))


@router.message_callback(F.callback.payload == FORM_SEND, RequestForm.confirm)
async def handle_send(
    event: MessageCallback, context: BaseContext, db: AsyncSession, user: User
) -> None:
    data = await context.get_data()
    try:
        ticket = await _service(db).create_request(
            user,
            category_id=data.get("category_id"),
            building_id=data.get("building_id"),
            apartment=data.get("apartment", ""),
            description=data.get("description", ""),
            preferred_time=data.get("preferred_time"),
            photo_ids=list(data.get("photo_ids", [])),
        )
    except AppException as exc:
        await context.clear()
        await _edit(event, exc.message, main_menu_keyboard())
        return
    await context.clear()
    await _edit(event, FORM_SENT.format(ticket_id=ticket.id))


@router.message_created(RequestForm, NOT_A_COMMAND)
async def handle_unexpected_message(
    event: MessageCreated, context: BaseContext, db: AsyncSession, user: User
) -> None:
    service = _service(db)
    state = await context.get_state()
    if state == RequestForm.category:
        await _ask_category(event, context, service)
    elif state == RequestForm.address:
        await _ask_address(event, context, user, service)
    elif state == RequestForm.building:
        await _ask_building(event, context, service)
    elif state == RequestForm.confirm:
        await _ask_confirm(event, context, service)


@router.message_callback(F.callback.payload.regexp(rf"^{FORM_PREFIX}"))
async def handle_stale_callback(event: MessageCallback) -> None:
    await event.ack(notification=OUTDATED_BUTTON_TEXT)
