from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from maxapi.context import MemoryContext
from maxapi.enums.attachment import AttachmentType
from maxapi.enums.message_link_type import MessageLinkType
from maxapi.filters import filter_attrs
from maxapi.types import MessageCallback, MessageCreated, RequestContactButton

from src.bot.handlers import request_form
from src.bot.keyboards import (
    FORM_ADDRESS_ADD,
    FORM_ADDRESS_OK,
    FORM_ADDRESS_OTHER,
    FORM_BUILDING_PREFIX,
    FORM_CANCEL,
    FORM_CATEGORY_PREFIX,
    FORM_PHOTOS_DONE,
    FORM_PHOTOS_SKIP,
    FORM_RESIDENCE_PREFIX,
    FORM_SEND,
    FORM_START,
    FORM_TIME_SKIP,
)
from src.bot.states import RequestForm
from src.bot.utils import NOT_A_COMMAND
from src.core.exceptions import AppException, MessengerException, NotFoundException
from src.core.texts import (
    DESCRIPTION_LIMIT,
    DESCRIPTION_REQUIRED,
    DESCRIPTION_TOO_LONG,
    FORM_ADDRESS_OTHER_PROMPT,
    FORM_ADDRESS_PROMPT,
    FORM_APARTMENT_PROMPT,
    FORM_BUILDING_PROMPT,
    FORM_CANCELLED,
    FORM_CATEGORY_PROMPT,
    FORM_DESCRIPTION_PROMPT,
    FORM_PHONE_OWN_TEXT,
    FORM_PHONE_PROMPT,
    FORM_PHOTO_FAILED,
    FORM_PHOTOS_ADDED,
    FORM_PHOTOS_LIMIT,
    FORM_PHOTOS_MAX,
    FORM_PHOTOS_PROMPT,
    FORM_SENT,
    FORM_TIME_PROMPT,
    OUTDATED_BUTTON_TEXT,
)

TICKET_ID = 1042


def _category(category_id: int, title: str) -> MagicMock:
    category = MagicMock()
    category.id = category_id
    category.title = title
    return category


def _building(building_id: int, address: str) -> MagicMock:
    building = MagicMock()
    building.id = building_id
    building.address = address
    return building


def _residence(
    residence_id: int,
    building_id: int,
    apartment: str,
    *,
    is_primary: bool = False,
) -> MagicMock:
    residence = MagicMock()
    residence.id = residence_id
    residence.building_id = building_id
    residence.apartment = apartment
    residence.is_primary = is_primary
    return residence


def _file(file_id: int) -> MagicMock:
    file = MagicMock()
    file.id = file_id
    return file


def _user(phone: str | None = "+79000000000") -> MagicMock:
    user = MagicMock()
    user.id = 1
    user.max_user_id = 42
    user.phone = phone
    return user


def _context() -> MemoryContext:
    return MemoryContext(chat_id=7, user_id=42)


def _callback(payload: str) -> MagicMock:
    event = MagicMock(spec=MessageCallback)
    event.edit = AsyncMock()
    event.ack = AsyncMock()
    callback = MagicMock()
    callback.payload = payload
    event.callback = callback
    return event


def _message(
    text: str | None = None,
    attachments: list | None = None,
    link_attachments: list | None = None,
) -> MagicMock:
    event = MagicMock(spec=MessageCreated)
    message = MagicMock()
    message.answer = AsyncMock()
    body = MagicMock()
    body.text = text
    body.attachments = attachments or []
    message.body = body
    if link_attachments is not None:
        link = MagicMock()
        link.type = MessageLinkType.FORWARD
        link.message.attachments = link_attachments
        message.link = link
    else:
        message.link = None
    event.message = message
    return event


def _contact_attachment(owner_id: int, phone: str | None) -> MagicMock:
    attachment = MagicMock()
    attachment.type = AttachmentType.CONTACT
    attachment.payload.max_info.user_id = owner_id
    attachment.payload.vcf.phone = phone
    return attachment


def _image_attachment(url: str) -> MagicMock:
    attachment = MagicMock()
    attachment.type = AttachmentType.IMAGE
    attachment.payload.url = url
    return attachment


def _rows(attachment) -> list:
    return attachment.payload.buttons


def _answer_text(event: MagicMock) -> str:
    return event.message.answer.await_args.args[0]


def _edit_text(event: MagicMock) -> str:
    return event.edit.await_args.kwargs["text"]


def _edit_rows(event: MagicMock) -> list:
    return _rows(event.edit.await_args.kwargs["attachments"][0])


def _answer_rows(event: MagicMock) -> list:
    return _rows(event.message.answer.await_args.kwargs["attachments"][0])


@pytest.fixture
def service() -> MagicMock:
    svc = MagicMock()
    svc.set_phone = AsyncMock()
    svc.list_categories = AsyncMock(
        return_value=[_category(1, "Сантехника"), _category(2, "Электрика")]
    )
    svc.list_buildings = AsyncMock(return_value=[_building(10, "ул. Ленина, 12")])
    svc.list_residences = AsyncMock(return_value=[])
    svc.add_residence = AsyncMock(return_value=_residence(5, 10, "45"))
    svc.get_residence = AsyncMock(return_value=_residence(4, 10, "7"))
    svc.save_photo = AsyncMock(return_value=_file(1))
    ticket = MagicMock()
    ticket.id = TICKET_ID
    svc.create_request = AsyncMock(return_value=ticket)
    with patch("src.bot.handlers.request_form.ClientTicketService", return_value=svc):
        yield svc


async def test_form_start_without_phone_asks_for_contact(service: MagicMock) -> None:
    event = _callback(FORM_START)
    context = _context()

    await request_form.handle_form_start(event, context, MagicMock(), _user(phone=None))

    assert await context.get_state() == RequestForm.phone
    assert _edit_text(event) == FORM_PHONE_PROMPT
    assert isinstance(_edit_rows(event)[0][0], RequestContactButton)
    assert _edit_rows(event)[1][0].payload == FORM_CANCEL
    service.set_phone.assert_not_awaited()


async def test_form_start_with_phone_asks_for_category(service: MagicMock) -> None:
    event = _callback(FORM_START)
    context = _context()

    await request_form.handle_form_start(event, context, MagicMock(), _user())

    assert await context.get_state() == RequestForm.category
    assert _edit_text(event) == FORM_CATEGORY_PROMPT
    assert [row[0].payload for row in _edit_rows(event)] == [
        f"{FORM_CATEGORY_PREFIX}1",
        f"{FORM_CATEGORY_PREFIX}2",
        FORM_CANCEL,
    ]


async def test_form_start_restarts_previous_form(service: MagicMock) -> None:
    event = _callback(FORM_START)
    context = _context()
    await context.set_state(RequestForm.confirm)
    await context.update_data(description="старое")

    await request_form.handle_form_start(event, context, MagicMock(), _user())

    assert "description" not in await context.get_data()


async def test_own_contact_saves_phone_and_asks_category(service: MagicMock) -> None:
    event = _message(attachments=[_contact_attachment(42, "79161234567")])
    context = _context()
    await context.set_state(RequestForm.phone)
    user = _user(phone=None)

    await request_form.handle_phone(event, context, MagicMock(), user)

    service.set_phone.assert_awaited_once_with(user, "79161234567")
    assert await context.get_state() == RequestForm.category
    assert _answer_text(event) == FORM_CATEGORY_PROMPT


async def test_foreign_contact_asks_for_own(service: MagicMock) -> None:
    event = _message(attachments=[_contact_attachment(999, "79161234567")])
    context = _context()
    await context.set_state(RequestForm.phone)

    await request_form.handle_phone(event, context, MagicMock(), _user(phone=None))

    service.set_phone.assert_not_awaited()
    assert await context.get_state() == RequestForm.phone
    assert _answer_text(event) == FORM_PHONE_OWN_TEXT


async def test_text_instead_of_contact_repeats_prompt(service: MagicMock) -> None:
    event = _message(text="привет")
    context = _context()
    await context.set_state(RequestForm.phone)

    await request_form.handle_phone(event, context, MagicMock(), _user(phone=None))

    service.set_phone.assert_not_awaited()
    assert await context.get_state() == RequestForm.phone
    assert _answer_text(event) == FORM_PHONE_PROMPT


async def test_invalid_phone_shows_service_message(service: MagicMock) -> None:
    service.set_phone.side_effect = AppException("Проверьте номер телефона", status_code=400)
    event = _message(attachments=[_contact_attachment(42, "123")])
    context = _context()
    await context.set_state(RequestForm.phone)

    await request_form.handle_phone(event, context, MagicMock(), _user(phone=None))

    assert _answer_text(event) == "Проверьте номер телефона"
    assert await context.get_state() == RequestForm.phone


async def test_category_without_residences_goes_to_building(service: MagicMock) -> None:
    event = _callback(f"{FORM_CATEGORY_PREFIX}1")
    context = _context()
    await context.set_state(RequestForm.category)

    await request_form.handle_category(event, context, MagicMock(), _user())

    assert (await context.get_data())["category_id"] == 1
    assert await context.get_state() == RequestForm.building
    assert _edit_text(event) == FORM_BUILDING_PROMPT
    assert _edit_rows(event)[0][0].payload == f"{FORM_BUILDING_PREFIX}10"


async def test_category_with_residences_shows_primary_address(service: MagicMock) -> None:
    service.list_residences.return_value = [_residence(3, 10, "45", is_primary=True)]
    event = _callback(f"{FORM_CATEGORY_PREFIX}1")
    context = _context()
    await context.set_state(RequestForm.category)

    await request_form.handle_category(event, context, MagicMock(), _user())

    assert await context.get_state() == RequestForm.address
    assert _edit_text(event) == FORM_ADDRESS_PROMPT.format(address="ул. Ленина, 12, кв. 45")
    assert [row[0].payload for row in _edit_rows(event)] == [
        FORM_ADDRESS_OK,
        FORM_ADDRESS_OTHER,
        FORM_CANCEL,
    ]


async def test_unknown_category_acks(service: MagicMock) -> None:
    event = _callback(f"{FORM_CATEGORY_PREFIX}99")
    context = _context()
    await context.set_state(RequestForm.category)

    await request_form.handle_category(event, context, MagicMock(), _user())

    event.ack.assert_awaited_once_with(notification=OUTDATED_BUTTON_TEXT)
    event.edit.assert_not_awaited()


async def test_non_numeric_category_payload_acks(service: MagicMock) -> None:
    event = _callback(f"{FORM_CATEGORY_PREFIX}abc")
    context = _context()
    await context.set_state(RequestForm.category)

    await request_form.handle_category(event, context, MagicMock(), _user())

    event.ack.assert_awaited_once_with(notification=OUTDATED_BUTTON_TEXT)
    event.edit.assert_not_awaited()


async def test_address_ok_uses_primary_residence(service: MagicMock) -> None:
    service.list_residences.return_value = [
        _residence(3, 10, "45", is_primary=True),
        _residence(4, 10, "7"),
    ]
    event = _callback(FORM_ADDRESS_OK)
    context = _context()
    await context.set_state(RequestForm.address)

    await request_form.handle_address_ok(event, context, MagicMock(), _user())

    data = await context.get_data()
    assert data["building_id"] == 10
    assert data["apartment"] == "45"
    assert await context.get_state() == RequestForm.description


async def test_address_other_lists_other_residences(service: MagicMock) -> None:
    service.list_residences.return_value = [
        _residence(3, 10, "45", is_primary=True),
        _residence(4, 10, "7"),
    ]
    event = _callback(FORM_ADDRESS_OTHER)
    context = _context()
    await context.set_state(RequestForm.address)

    await request_form.handle_address_other(event, context, MagicMock(), _user())

    assert _edit_text(event) == FORM_ADDRESS_OTHER_PROMPT
    assert [row[0].payload for row in _edit_rows(event)] == [
        f"{FORM_RESIDENCE_PREFIX}4",
        FORM_ADDRESS_ADD,
        FORM_CANCEL,
    ]


async def test_address_add_goes_to_building(service: MagicMock) -> None:
    event = _callback(FORM_ADDRESS_ADD)
    context = _context()
    await context.set_state(RequestForm.address)

    await request_form.handle_address_add(event, context, MagicMock(), _user())

    assert await context.get_state() == RequestForm.building
    assert _edit_text(event) == FORM_BUILDING_PROMPT


async def test_residence_choice_sets_address(service: MagicMock) -> None:
    service.get_residence.return_value = _residence(4, 10, "7")
    event = _callback(f"{FORM_RESIDENCE_PREFIX}4")
    context = _context()
    await context.set_state(RequestForm.address)

    await request_form.handle_residence(event, context, MagicMock(), _user())

    service.get_residence.assert_awaited_once()
    data = await context.get_data()
    assert data["building_id"] == 10
    assert data["apartment"] == "7"
    assert await context.get_state() == RequestForm.description


async def test_foreign_residence_acks(service: MagicMock) -> None:
    service.get_residence.side_effect = NotFoundException()
    event = _callback(f"{FORM_RESIDENCE_PREFIX}99")
    context = _context()
    await context.set_state(RequestForm.address)

    await request_form.handle_residence(event, context, MagicMock(), _user())

    event.ack.assert_awaited_once_with(notification=OUTDATED_BUTTON_TEXT)
    event.edit.assert_not_awaited()


async def test_building_choice_goes_to_apartment(service: MagicMock) -> None:
    event = _callback(f"{FORM_BUILDING_PREFIX}10")
    context = _context()
    await context.set_state(RequestForm.building)

    await request_form.handle_building(event, context, MagicMock(), _user())

    assert (await context.get_data())["building_id"] == 10
    assert await context.get_state() == RequestForm.apartment
    assert _edit_text(event) == FORM_APARTMENT_PROMPT


async def test_unknown_building_acks(service: MagicMock) -> None:
    service.list_buildings.return_value = []
    event = _callback(f"{FORM_BUILDING_PREFIX}999")
    context = _context()
    await context.set_state(RequestForm.building)

    await request_form.handle_building(event, context, MagicMock(), _user())

    event.ack.assert_awaited_once_with(notification=OUTDATED_BUTTON_TEXT)
    event.edit.assert_not_awaited()


@pytest.mark.parametrize("payload", [f"{FORM_BUILDING_PREFIX}0", f"{FORM_BUILDING_PREFIX}{2**63}"])
async def test_out_of_range_building_payload_acks(service: MagicMock, payload: str) -> None:
    event = _callback(payload)
    context = _context()
    await context.set_state(RequestForm.building)

    await request_form.handle_building(event, context, MagicMock(), _user())

    event.ack.assert_awaited_once_with(notification=OUTDATED_BUTTON_TEXT)
    event.edit.assert_not_awaited()


async def test_apartment_saves_residence_and_asks_description(service: MagicMock) -> None:
    service.add_residence.return_value = _residence(5, 10, "45")
    event = _message(text=" 45 ")
    context = _context()
    await context.set_state(RequestForm.apartment)
    await context.update_data(building_id=10)
    user = _user()

    await request_form.handle_apartment(event, context, MagicMock(), user)

    service.add_residence.assert_awaited_once_with(user, 10, "45")
    data = await context.get_data()
    assert data["building_id"] == 10
    assert data["apartment"] == "45"
    assert await context.get_state() == RequestForm.description
    assert _answer_text(event) == FORM_DESCRIPTION_PROMPT


async def test_invalid_apartment_shows_message_and_stays(service: MagicMock) -> None:
    service.add_residence.side_effect = AppException("Квартира — до 20 символов", status_code=400)
    event = _message(text="?")
    context = _context()
    await context.set_state(RequestForm.apartment)
    await context.update_data(building_id=10)

    await request_form.handle_apartment(event, context, MagicMock(), _user())

    assert _answer_text(event) == "Квартира — до 20 символов"
    assert await context.get_state() == RequestForm.apartment


async def test_unknown_building_at_apartment_returns_to_building(service: MagicMock) -> None:
    service.add_residence.side_effect = NotFoundException()
    event = _message(text="45")
    context = _context()
    await context.set_state(RequestForm.apartment)
    await context.update_data(building_id=10)

    await request_form.handle_apartment(event, context, MagicMock(), _user())

    assert await context.get_state() == RequestForm.building
    assert _answer_text(event) == FORM_BUILDING_PROMPT


async def test_empty_description_shows_error_and_stays(service: MagicMock) -> None:
    event = _message(text="   ")
    context = _context()
    await context.set_state(RequestForm.description)

    await request_form.handle_description(event, context, MagicMock(), _user())

    assert "description" not in await context.get_data()
    assert await context.get_state() == RequestForm.description
    assert _answer_text(event) == DESCRIPTION_REQUIRED
    assert [row[0].payload for row in _answer_rows(event)] == [FORM_CANCEL]


async def test_too_long_description_shows_error_and_stays(service: MagicMock) -> None:
    event = _message(text="a" * (DESCRIPTION_LIMIT + 1))
    context = _context()
    await context.set_state(RequestForm.description)

    await request_form.handle_description(event, context, MagicMock(), _user())

    assert "description" not in await context.get_data()
    assert await context.get_state() == RequestForm.description
    assert _answer_text(event) == DESCRIPTION_TOO_LONG
    assert [row[0].payload for row in _answer_rows(event)] == [FORM_CANCEL]


async def test_description_saved_and_asks_photos(service: MagicMock) -> None:
    event = _message(text="  Течёт кран ")
    context = _context()
    await context.set_state(RequestForm.description)

    await request_form.handle_description(event, context, MagicMock(), _user())

    assert (await context.get_data())["description"] == "Течёт кран"
    assert await context.get_state() == RequestForm.photos
    assert _answer_text(event) == FORM_PHOTOS_PROMPT
    assert [row[0].payload for row in _answer_rows(event)] == [FORM_PHOTOS_SKIP, FORM_CANCEL]


async def test_photos_are_saved_and_counted(service: MagicMock) -> None:
    service.save_photo.side_effect = [_file(1), _file(2)]
    event = _message(
        attachments=[
            _image_attachment("https://i.oneme.ru/1"),
            _image_attachment("https://i.oneme.ru/2"),
        ]
    )
    context = _context()
    await context.set_state(RequestForm.photos)

    await request_form.handle_photos(event, context, MagicMock(), _user())

    assert (await context.get_data())["photo_ids"] == [1, 2]
    assert await context.get_state() == RequestForm.photos
    assert _answer_text(event) == FORM_PHOTOS_ADDED.format(count=2)
    assert [row[0].payload for row in _answer_rows(event)] == [FORM_PHOTOS_DONE, FORM_CANCEL]


async def test_forwarded_photo_is_saved(service: MagicMock) -> None:
    event = _message(link_attachments=[_image_attachment("https://i.oneme.ru/fwd")])
    context = _context()
    await context.set_state(RequestForm.photos)

    await request_form.handle_photos(event, context, MagicMock(), _user())

    service.save_photo.assert_awaited_once_with("https://i.oneme.ru/fwd")
    assert (await context.get_data())["photo_ids"] == [1]


async def test_photo_without_images_repeats_prompt(service: MagicMock) -> None:
    event = _message(text="фото")
    context = _context()
    await context.set_state(RequestForm.photos)

    await request_form.handle_photos(event, context, MagicMock(), _user())

    service.save_photo.assert_not_awaited()
    assert await context.get_state() == RequestForm.photos
    assert _answer_text(event) == FORM_PHOTOS_PROMPT
    assert [row[0].payload for row in _answer_rows(event)] == [FORM_PHOTOS_SKIP, FORM_CANCEL]


async def test_photo_without_images_after_photos_offers_done(service: MagicMock) -> None:
    event = _message(text="ещё фото")
    context = _context()
    await context.set_state(RequestForm.photos)
    await context.update_data(photo_ids=[1])

    await request_form.handle_photos(event, context, MagicMock(), _user())

    service.save_photo.assert_not_awaited()
    assert _answer_text(event) == FORM_PHOTOS_PROMPT
    assert [row[0].payload for row in _answer_rows(event)] == [FORM_PHOTOS_DONE, FORM_CANCEL]


async def test_eleventh_photo_is_refused(service: MagicMock) -> None:
    existing = list(range(1, FORM_PHOTOS_MAX + 1))
    event = _message(attachments=[_image_attachment("https://i.oneme.ru/11")])
    context = _context()
    await context.set_state(RequestForm.photos)
    await context.update_data(photo_ids=existing)

    await request_form.handle_photos(event, context, MagicMock(), _user())

    service.save_photo.assert_not_awaited()
    assert (await context.get_data())["photo_ids"] == existing
    assert _answer_text(event) == FORM_PHOTOS_LIMIT.format(
        max=FORM_PHOTOS_MAX, count=FORM_PHOTOS_MAX
    )
    assert [row[0].payload for row in _answer_rows(event)] == [FORM_PHOTOS_DONE, FORM_CANCEL]


async def test_photo_limit_reports_total_including_new(service: MagicMock) -> None:
    existing = list(range(1, FORM_PHOTOS_MAX))
    service.save_photo.side_effect = [_file(FORM_PHOTOS_MAX)]
    event = _message(
        attachments=[
            _image_attachment("https://i.oneme.ru/10"),
            _image_attachment("https://i.oneme.ru/11"),
        ]
    )
    context = _context()
    await context.set_state(RequestForm.photos)
    await context.update_data(photo_ids=existing)

    await request_form.handle_photos(event, context, MagicMock(), _user())

    assert (await context.get_data())["photo_ids"] == existing + [FORM_PHOTOS_MAX]
    assert _answer_text(event) == FORM_PHOTOS_LIMIT.format(
        max=FORM_PHOTOS_MAX, count=FORM_PHOTOS_MAX
    )
    assert [row[0].payload for row in _answer_rows(event)] == [FORM_PHOTOS_DONE, FORM_CANCEL]


async def test_failed_photo_download_keeps_step(service: MagicMock) -> None:
    service.save_photo.side_effect = MessengerException()
    event = _message(attachments=[_image_attachment("https://i.oneme.ru/1")])
    context = _context()
    await context.set_state(RequestForm.photos)

    await request_form.handle_photos(event, context, MagicMock(), _user())

    assert (await context.get_data()).get("photo_ids", []) == []
    assert await context.get_state() == RequestForm.photos
    assert _answer_text(event) == FORM_PHOTO_FAILED.format(count=0)
    assert [row[0].payload for row in _answer_rows(event)] == [FORM_PHOTOS_SKIP, FORM_CANCEL]


async def test_partially_failed_photos_report_total(service: MagicMock) -> None:
    service.save_photo.side_effect = [_file(1), MessengerException()]
    event = _message(
        attachments=[
            _image_attachment("https://i.oneme.ru/1"),
            _image_attachment("https://i.oneme.ru/2"),
        ]
    )
    context = _context()
    await context.set_state(RequestForm.photos)

    await request_form.handle_photos(event, context, MagicMock(), _user())

    assert (await context.get_data())["photo_ids"] == [1]
    assert _answer_text(event) == FORM_PHOTO_FAILED.format(count=1)
    assert [row[0].payload for row in _answer_rows(event)] == [FORM_PHOTOS_DONE, FORM_CANCEL]


async def test_photos_done_asks_time(service: MagicMock) -> None:
    event = _callback(FORM_PHOTOS_DONE)
    context = _context()
    await context.set_state(RequestForm.photos)

    await request_form.handle_photos_done(event, context, MagicMock(), _user())

    assert await context.get_state() == RequestForm.preferred_time
    assert _edit_text(event) == FORM_TIME_PROMPT


async def test_photos_skip_asks_time(service: MagicMock) -> None:
    event = _callback(FORM_PHOTOS_SKIP)
    context = _context()
    await context.set_state(RequestForm.photos)

    await request_form.handle_photos_skip(event, context, MagicMock(), _user())

    assert await context.get_state() == RequestForm.preferred_time


async def test_time_text_saved_and_confirmed(service: MagicMock) -> None:
    event = _message(text="вечером")
    context = _context()
    await context.set_state(RequestForm.preferred_time)

    await request_form.handle_time(event, context, MagicMock(), _user())

    assert (await context.get_data())["preferred_time"] == "вечером"
    assert await context.get_state() == RequestForm.confirm
    assert "вечером" in _answer_text(event)


async def test_time_skip_goes_to_confirm(service: MagicMock) -> None:
    event = _callback(FORM_TIME_SKIP)
    context = _context()
    await context.set_state(RequestForm.preferred_time)

    await request_form.handle_time_skip(event, context, MagicMock(), _user())

    assert (await context.get_data())["preferred_time"] is None
    assert await context.get_state() == RequestForm.confirm
    assert "не указано" in _edit_text(event)


async def test_send_creates_request_and_clears_context(service: MagicMock) -> None:
    event = _callback(FORM_SEND)
    context = _context()
    await context.set_state(RequestForm.confirm)
    await context.update_data(
        category_id=1,
        building_id=10,
        apartment="45",
        description="Течёт кран",
        preferred_time="вечером",
        photo_ids=[1, 2],
    )
    user = _user()

    await request_form.handle_send(event, context, MagicMock(), user)

    service.create_request.assert_awaited_once_with(
        user,
        category_id=1,
        building_id=10,
        apartment="45",
        description="Течёт кран",
        preferred_time="вечером",
        photo_ids=[1, 2],
    )
    assert await context.get_state() is None
    assert await context.get_data() == {}
    assert _edit_text(event) == FORM_SENT.format(ticket_id=TICKET_ID)
    assert event.edit.await_args.kwargs["attachments"] == []


async def test_send_service_error_shows_message_and_menu(service: MagicMock) -> None:
    service.create_request.side_effect = AppException("Категория не найдена", status_code=404)
    event = _callback(FORM_SEND)
    context = _context()
    await context.set_state(RequestForm.confirm)
    await context.update_data(category_id=99, building_id=10, apartment="45", description="x")

    await request_form.handle_send(event, context, MagicMock(), _user())

    assert await context.get_state() is None
    assert _edit_text(event) == "Категория не найдена"
    assert _edit_rows(event)[0][0].payload == FORM_START


async def test_cancel_clears_context_and_shows_menu(service: MagicMock) -> None:
    event = _callback(FORM_CANCEL)
    context = _context()
    await context.set_state(RequestForm.category)

    await request_form.handle_form_cancel(event, context, MagicMock(), _user())

    assert await context.get_state() is None
    assert await context.get_data() == {}
    assert _edit_text(event) == FORM_CANCELLED
    assert _edit_rows(event)[0][0].payload == FORM_START


async def test_stale_form_callback_acks(service: MagicMock) -> None:
    event = _callback(f"{FORM_CATEGORY_PREFIX}1")

    await request_form.handle_stale_callback(event)

    event.ack.assert_awaited_once_with(notification=OUTDATED_BUTTON_TEXT)
    event.edit.assert_not_awaited()


async def test_unexpected_message_in_category_repeats_prompt(service: MagicMock) -> None:
    event = _message(text="привет")
    context = _context()
    await context.set_state(RequestForm.category)

    await request_form.handle_unexpected_message(event, context, MagicMock(), _user())

    assert await context.get_state() == RequestForm.category
    assert _answer_text(event) == FORM_CATEGORY_PROMPT
    assert [
        row[0].payload for row in _rows(event.message.answer.await_args.kwargs["attachments"][0])
    ] == [
        f"{FORM_CATEGORY_PREFIX}1",
        f"{FORM_CATEGORY_PREFIX}2",
        FORM_CANCEL,
    ]


def test_not_a_command_filter_skips_commands() -> None:
    start = SimpleNamespace(message=SimpleNamespace(body=SimpleNamespace(text="/start")))
    text = SimpleNamespace(message=SimpleNamespace(body=SimpleNamespace(text="привет")))

    assert filter_attrs(start, NOT_A_COMMAND) is False
    assert filter_attrs(text, NOT_A_COMMAND) is True
