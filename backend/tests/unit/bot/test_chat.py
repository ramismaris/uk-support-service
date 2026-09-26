from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from maxapi.context import MemoryContext
from maxapi.enums.attachment import AttachmentType
from maxapi.enums.message_link_type import MessageLinkType
from maxapi.types import MessageCallback, MessageCreated
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.handlers import chat
from src.bot.keyboards import (
    CHAT_CANCEL,
    CHAT_CHOOSE_PREFIX,
    CHAT_QUESTION,
)
from src.bot.states import ChatStates
from src.core.constants import CHAT_TICKET_PREFIX, TicketType
from src.core.exceptions import AppException, ConflictException, MessengerException
from src.core.texts import (
    CHAT_CHOOSE_TICKET,
    CHAT_FINISH_CURRENT,
    CHAT_NOT_SENT,
    CHAT_OFFER_QUESTION,
    CHAT_PHOTOS_ALL_FAILED,
    CHAT_PHOTOS_FAILED,
    CHAT_SENT,
    CHAT_TEXT_REQUIRED,
    CHAT_UNSUPPORTED,
    CHAT_WRITE_NOTIFICATION,
    CHAT_WRITE_PROMPT,
    FORM_PHOTOS_MAX,
    OUTDATED_BUTTON_TEXT,
    QUESTION_SENT,
    TICKET_CLOSED_FOR_CLIENT,
    TICKET_NOT_FOUND,
    ticket_dative,
)
from src.services.ticket_rules import AskWhichTicket, OfferNewQuestion, ToTicket

TICKET_ID = 1042
QUESTION_ID = 1051


def _user() -> MagicMock:
    user = MagicMock()
    user.id = 1
    user.max_user_id = 42
    user.phone = "+79000000000"
    return user


def _context() -> MemoryContext:
    return MemoryContext(chat_id=7, user_id=42)


def _ticket(
    ticket_id: int,
    ticket_type: TicketType = TicketType.REQUEST,
    category_title: str | None = "Сантехника",
) -> SimpleNamespace:
    category = None if category_title is None else SimpleNamespace(title=category_title)
    return SimpleNamespace(id=ticket_id, type=ticket_type, category=category)


def _file(file_id: int) -> MagicMock:
    file = MagicMock()
    file.id = file_id
    return file


def _image_attachment(url: str) -> MagicMock:
    attachment = MagicMock()
    attachment.type = AttachmentType.IMAGE
    attachment.payload.url = url
    return attachment


def _sticker_attachment() -> MagicMock:
    attachment = MagicMock()
    attachment.type = AttachmentType.STICKER
    return attachment


def _message(
    text: str | None = None,
    attachments: list | None = None,
    *,
    mid: str = "m1",
    link_type: MessageLinkType | None = None,
    link_text: str | None = None,
    link_attachments: list | None = None,
    link_mid: str = "lm1",
) -> MagicMock:
    event = MagicMock(spec=MessageCreated)
    message = MagicMock()
    message.answer = AsyncMock()
    body = MagicMock()
    body.mid = mid
    body.text = text
    body.attachments = attachments or []
    message.body = body
    if link_type is not None:
        link = MagicMock()
        link.type = link_type
        link.message.mid = link_mid
        link.message.text = link_text
        link.message.attachments = link_attachments or []
        message.link = link
    else:
        message.link = None
    event.message = message
    return event


def _callback(payload: str) -> MagicMock:
    event = MagicMock(spec=MessageCallback)
    event.edit = AsyncMock()
    event.ack = AsyncMock()
    event.send = AsyncMock()
    callback = MagicMock()
    callback.payload = payload
    event.callback = callback
    return event


def _answer_texts(event: MagicMock) -> list[str]:
    return [call.args[0] for call in event.message.answer.await_args_list]


def _last_answer_text(event: MagicMock) -> str:
    return event.message.answer.await_args.args[0]


def _answer_rows(event: MagicMock, index: int = 0) -> list:
    return event.message.answer.await_args_list[index].kwargs["attachments"][0].payload.buttons


def _edit_text(event: MagicMock) -> str:
    return event.edit.await_args.kwargs["text"]


def _edit_rows(event: MagicMock) -> list:
    return event.edit.await_args.kwargs["attachments"][0].payload.buttons


@pytest.fixture
def services() -> SimpleNamespace:
    client_service = MagicMock()
    client_service.save_photo = AsyncMock(return_value=_file(1))
    client_service.list_open_tickets = AsyncMock(return_value=[_ticket(TICKET_ID)])
    client_service.get_ticket = AsyncMock(return_value=_ticket(TICKET_ID))
    client_service.create_question = AsyncMock(
        return_value=_ticket(QUESTION_ID, TicketType.QUESTION, None)
    )
    client_service.set_active_ticket = AsyncMock(return_value=_ticket(TICKET_ID))

    message_service = MagicMock()
    message_service.resolve_client_route = AsyncMock()
    message_service.add_client_message = AsyncMock()

    with (
        patch("src.bot.handlers.chat.ClientTicketService", return_value=client_service),
        patch("src.bot.handlers.chat.MessageService", return_value=message_service),
    ):
        yield SimpleNamespace(client=client_service, message=message_service)


def _db() -> MagicMock:
    return MagicMock(spec=AsyncSession)


async def test_free_message_routes_to_ticket_and_answers(services: SimpleNamespace) -> None:
    services.message.resolve_client_route.return_value = ToTicket(TICKET_ID)
    services.client.list_open_tickets.return_value = [_ticket(TICKET_ID)]
    event = _message(text="Течёт кран", mid="m1")
    context = _context()
    user = _user()

    await chat.handle_free_message(event, context, _db(), user)

    services.message.resolve_client_route.assert_awaited_once_with(user, None)
    services.client.save_photo.assert_not_awaited()
    services.message.add_client_message.assert_awaited_once_with(
        user,
        TICKET_ID,
        text="Течёт кран",
        file_ids=[],
        max_message_id="m1",
    )
    assert await context.get_state() is None
    assert _answer_texts(event) == [
        CHAT_SENT.format(label=ticket_dative(TicketType.REQUEST, TICKET_ID))
    ]


async def test_free_message_passes_reply_mid_and_strips_text(services: SimpleNamespace) -> None:
    services.message.resolve_client_route.return_value = ToTicket(TICKET_ID)
    event = _message(
        text="  ответ  ",
        link_type=MessageLinkType.REPLY,
        link_mid="staff-mid",
    )
    user = _user()

    await chat.handle_free_message(event, _context(), _db(), user)

    services.message.resolve_client_route.assert_awaited_once_with(user, "staff-mid")
    assert services.message.add_client_message.await_args.kwargs["text"] == "ответ"


async def test_free_message_reply_does_not_save_quoted_photos(
    services: SimpleNamespace,
) -> None:
    services.message.resolve_client_route.return_value = ToTicket(TICKET_ID)
    event = _message(
        text="ответ",
        link_type=MessageLinkType.REPLY,
        link_attachments=[_image_attachment("https://i.oneme.ru/staff")],
    )

    await chat.handle_free_message(event, _context(), _db(), _user())

    services.client.save_photo.assert_not_awaited()
    assert services.message.add_client_message.await_args.kwargs["file_ids"] == []


async def test_free_message_forward_link_is_not_a_reply(services: SimpleNamespace) -> None:
    services.message.resolve_client_route.return_value = ToTicket(TICKET_ID)
    event = _message(
        text="смотрите",
        link_type=MessageLinkType.FORWARD,
        link_mid="forwarded-mid",
    )
    user = _user()

    await chat.handle_free_message(event, _context(), _db(), user)

    services.message.resolve_client_route.assert_awaited_once_with(user, None)


async def test_free_message_without_content_is_unsupported(services: SimpleNamespace) -> None:
    event = _message(attachments=[_sticker_attachment()])

    await chat.handle_free_message(event, _context(), _db(), _user())

    assert _answer_texts(event) == [CHAT_UNSUPPORTED]
    services.message.resolve_client_route.assert_not_awaited()
    services.message.add_client_message.assert_not_awaited()


async def test_free_message_saves_photos(services: SimpleNamespace) -> None:
    services.message.resolve_client_route.return_value = ToTicket(TICKET_ID)
    services.client.save_photo.side_effect = [_file(11), _file(12)]
    event = _message(
        text="фото",
        attachments=[
            _image_attachment("https://i.oneme.ru/1"),
            _image_attachment("https://i.oneme.ru/2"),
        ],
    )

    await chat.handle_free_message(event, _context(), _db(), _user())

    assert services.client.save_photo.await_count == 2
    assert services.message.add_client_message.await_args.kwargs["file_ids"] == [11, 12]
    assert _answer_texts(event) == [
        CHAT_SENT.format(label=ticket_dative(TicketType.REQUEST, TICKET_ID))
    ]


async def test_free_message_forwarded_photo_is_saved(services: SimpleNamespace) -> None:
    services.message.resolve_client_route.return_value = ToTicket(TICKET_ID)
    event = _message(
        link_type=MessageLinkType.FORWARD,
        link_attachments=[_image_attachment("https://i.oneme.ru/fwd")],
    )

    await chat.handle_free_message(event, _context(), _db(), _user())

    services.client.save_photo.assert_awaited_once_with("https://i.oneme.ru/fwd")
    assert services.message.add_client_message.await_args.kwargs["file_ids"] == [1]


async def test_free_message_limits_photo_count(services: SimpleNamespace) -> None:
    services.message.resolve_client_route.return_value = ToTicket(TICKET_ID)
    event = _message(
        text="много",
        attachments=[
            _image_attachment(f"https://i.oneme.ru/{index}") for index in range(FORM_PHOTOS_MAX + 3)
        ],
    )

    await chat.handle_free_message(event, _context(), _db(), _user())

    assert services.client.save_photo.await_count == FORM_PHOTOS_MAX
    assert len(services.message.add_client_message.await_args.kwargs["file_ids"]) == FORM_PHOTOS_MAX


async def test_free_message_partial_photo_failure_warns(
    services: SimpleNamespace,
) -> None:
    services.message.resolve_client_route.return_value = ToTicket(TICKET_ID)
    services.client.save_photo.side_effect = [_file(11), MessengerException()]
    event = _message(
        text="текст",
        attachments=[
            _image_attachment("https://i.oneme.ru/1"),
            _image_attachment("https://i.oneme.ru/2"),
        ],
    )

    await chat.handle_free_message(event, _context(), _db(), _user())

    assert services.message.add_client_message.await_args.kwargs["file_ids"] == [11]
    assert _answer_texts(event) == [
        CHAT_SENT.format(label=ticket_dative(TicketType.REQUEST, TICKET_ID)),
        CHAT_PHOTOS_FAILED,
    ]


async def test_free_message_all_photos_failed_without_text_saves_nothing(
    services: SimpleNamespace,
) -> None:
    services.message.resolve_client_route.return_value = ToTicket(TICKET_ID)
    services.client.save_photo.side_effect = MessengerException()
    event = _message(attachments=[_image_attachment("https://i.oneme.ru/1")])

    await chat.handle_free_message(event, _context(), _db(), _user())

    assert _answer_texts(event) == [CHAT_PHOTOS_ALL_FAILED]
    services.message.add_client_message.assert_not_awaited()


async def test_free_message_all_photos_failed_with_text_still_sends(
    services: SimpleNamespace,
) -> None:
    services.message.resolve_client_route.return_value = ToTicket(TICKET_ID)
    services.client.save_photo.side_effect = MessengerException()
    event = _message(
        text="текст",
        attachments=[_image_attachment("https://i.oneme.ru/1")],
    )

    await chat.handle_free_message(event, _context(), _db(), _user())

    assert services.message.add_client_message.await_args.kwargs["file_ids"] == []
    assert _answer_texts(event) == [
        CHAT_SENT.format(label=ticket_dative(TicketType.REQUEST, TICKET_ID)),
        CHAT_PHOTOS_FAILED,
    ]


async def test_free_message_service_error_is_answered(services: SimpleNamespace) -> None:
    services.message.resolve_client_route.return_value = ToTicket(TICKET_ID)
    services.message.add_client_message.side_effect = ConflictException(
        TICKET_CLOSED_FOR_CLIENT.format(ticket_id=TICKET_ID)
    )
    event = _message(text="текст")

    await chat.handle_free_message(event, _context(), _db(), _user())

    assert _answer_texts(event) == [TICKET_CLOSED_FOR_CLIENT.format(ticket_id=TICKET_ID)]


async def test_free_message_offer_question_with_text(services: SimpleNamespace) -> None:
    services.message.resolve_client_route.return_value = OfferNewQuestion()
    event = _message(text="Когда отключат воду?", mid="m9")
    context = _context()

    await chat.handle_free_message(event, context, _db(), _user())

    assert await context.get_state() == ChatStates.confirm_question
    assert (await context.get_data()) == {
        "text": "Когда отключат воду?",
        "file_ids": [],
        "max_message_id": "m9",
    }
    assert _answer_texts(event) == [CHAT_OFFER_QUESTION]
    rows = _answer_rows(event)
    assert [row[0].payload for row in rows] == [CHAT_QUESTION, CHAT_CANCEL]


async def test_free_message_offer_question_without_text_asks_for_text(
    services: SimpleNamespace,
) -> None:
    services.message.resolve_client_route.return_value = OfferNewQuestion()
    event = _message(attachments=[_image_attachment("https://i.oneme.ru/1")])
    context = _context()

    await chat.handle_free_message(event, context, _db(), _user())

    assert await context.get_state() is None
    assert _answer_texts(event) == [CHAT_TEXT_REQUIRED]
    services.client.save_photo.assert_not_awaited()
    assert _answer_rows(event)[0][0].payload == "form:start"


async def test_free_message_ask_which_ticket_with_text(services: SimpleNamespace) -> None:
    services.message.resolve_client_route.return_value = AskWhichTicket((TICKET_ID, QUESTION_ID))
    services.client.list_open_tickets.return_value = [
        _ticket(TICKET_ID),
        _ticket(QUESTION_ID, TicketType.QUESTION, None),
    ]
    event = _message(text="сообщение", mid="m5")
    context = _context()

    await chat.handle_free_message(event, context, _db(), _user())

    assert await context.get_state() == ChatStates.choose_ticket
    assert (await context.get_data())["max_message_id"] == "m5"
    assert _answer_texts(event) == [CHAT_CHOOSE_TICKET]
    rows = _answer_rows(event)
    assert [row[0].text for row in rows] == [
        "№1042 · Сантехника",
        "№1051 · Вопрос",
        "Новый вопрос",
        "Отменить",
    ]
    assert [row[0].payload for row in rows] == [
        f"{CHAT_CHOOSE_PREFIX}{TICKET_ID}",
        f"{CHAT_CHOOSE_PREFIX}{QUESTION_ID}",
        CHAT_QUESTION,
        CHAT_CANCEL,
    ]


async def test_free_message_ask_which_ticket_without_text_hides_question(
    services: SimpleNamespace,
) -> None:
    services.message.resolve_client_route.return_value = AskWhichTicket((TICKET_ID,))
    services.client.list_open_tickets.return_value = [_ticket(TICKET_ID)]
    event = _message(attachments=[_image_attachment("https://i.oneme.ru/1")])

    await chat.handle_free_message(event, _context(), _db(), _user())

    rows = _answer_rows(event)
    assert [row[0].payload for row in rows] == [
        f"{CHAT_CHOOSE_PREFIX}{TICKET_ID}",
        CHAT_CANCEL,
    ]


async def test_free_message_ask_which_ticket_all_photos_failed(
    services: SimpleNamespace,
) -> None:
    services.message.resolve_client_route.return_value = AskWhichTicket((TICKET_ID,))
    services.client.save_photo.side_effect = MessengerException()
    event = _message(attachments=[_image_attachment("https://i.oneme.ru/1")])
    context = _context()

    await chat.handle_free_message(event, context, _db(), _user())

    assert _answer_texts(event) == [CHAT_PHOTOS_ALL_FAILED]
    assert await context.get_state() is None


async def test_choose_ticket_sends_pending_message(services: SimpleNamespace) -> None:
    services.client.list_open_tickets.return_value = [_ticket(TICKET_ID)]
    event = _callback(f"{CHAT_CHOOSE_PREFIX}{TICKET_ID}")
    context = _context()
    await context.set_state(ChatStates.choose_ticket)
    await context.update_data(text="Привет", file_ids=[5], max_message_id="m7")
    user = _user()

    await chat.handle_choose_ticket(event, context, _db(), user)

    services.message.add_client_message.assert_awaited_once_with(
        user,
        TICKET_ID,
        text="Привет",
        file_ids=[5],
        max_message_id="m7",
    )
    assert await context.get_state() is None
    assert _edit_text(event) == CHAT_SENT.format(label=ticket_dative(TicketType.REQUEST, TICKET_ID))
    assert event.edit.await_args.kwargs["attachments"] == []


async def test_choose_ticket_without_text_passes_none(services: SimpleNamespace) -> None:
    event = _callback(f"{CHAT_CHOOSE_PREFIX}{TICKET_ID}")
    context = _context()
    await context.set_state(ChatStates.choose_ticket)
    await context.update_data(text="", file_ids=[5], max_message_id="m7")

    await chat.handle_choose_ticket(event, context, _db(), _user())

    assert services.message.add_client_message.await_args.kwargs["text"] is None


async def test_choose_ticket_closed_service_error_clears_state(
    services: SimpleNamespace,
) -> None:
    message = TICKET_CLOSED_FOR_CLIENT.format(ticket_id=TICKET_ID)
    services.message.add_client_message.side_effect = ConflictException(message)
    event = _callback(f"{CHAT_CHOOSE_PREFIX}{TICKET_ID}")
    context = _context()
    await context.set_state(ChatStates.choose_ticket)
    await context.update_data(text="Привет", file_ids=[], max_message_id="m7")

    await chat.handle_choose_ticket(event, context, _db(), _user())

    assert await context.get_state() is None
    assert _edit_text(event) == message


async def test_choose_ticket_foreign_ticket_404(services: SimpleNamespace) -> None:
    services.message.add_client_message.side_effect = AppException(
        TICKET_NOT_FOUND, status_code=404
    )
    event = _callback(f"{CHAT_CHOOSE_PREFIX}{TICKET_ID}")
    context = _context()
    await context.set_state(ChatStates.choose_ticket)
    await context.update_data(text="Привет", file_ids=[], max_message_id="m7")

    await chat.handle_choose_ticket(event, context, _db(), _user())

    assert _edit_text(event) == TICKET_NOT_FOUND


@pytest.mark.parametrize(
    "payload",
    [f"{CHAT_CHOOSE_PREFIX}abc", f"{CHAT_CHOOSE_PREFIX}0", f"{CHAT_CHOOSE_PREFIX}{2**63}"],
)
async def test_choose_ticket_bad_id_acks(services: SimpleNamespace, payload: str) -> None:
    event = _callback(payload)
    context = _context()
    await context.set_state(ChatStates.choose_ticket)
    await context.update_data(text="Привет", file_ids=[], max_message_id="m7")

    await chat.handle_choose_ticket(event, context, _db(), _user())

    event.ack.assert_awaited_once_with(notification=OUTDATED_BUTTON_TEXT)
    event.edit.assert_not_awaited()
    services.message.add_client_message.assert_not_awaited()


async def test_question_creates_from_pending_message(services: SimpleNamespace) -> None:
    event = _callback(CHAT_QUESTION)
    context = _context()
    await context.set_state(ChatStates.confirm_question)
    await context.update_data(text="Когда отключат воду?", file_ids=[3, 4], max_message_id="m9")
    user = _user()

    await chat.handle_question(event, context, _db(), user)

    services.client.create_question.assert_awaited_once_with(
        user,
        description="Когда отключат воду?",
        photo_ids=[3, 4],
    )
    assert await context.get_state() is None
    assert _edit_text(event) == QUESTION_SENT.format(ticket_id=QUESTION_ID)


async def test_question_from_choose_state(services: SimpleNamespace) -> None:
    event = _callback(CHAT_QUESTION)
    context = _context()
    await context.set_state(ChatStates.choose_ticket)
    await context.update_data(text="Вопрос", file_ids=[], max_message_id="m9")

    await chat.handle_question(event, context, _db(), _user())

    services.client.create_question.assert_awaited_once()
    assert await context.get_state() is None
    assert _edit_text(event) == QUESTION_SENT.format(ticket_id=QUESTION_ID)


async def test_question_service_error_clears_state(services: SimpleNamespace) -> None:
    services.client.create_question.side_effect = AppException("Опишите проблему", status_code=400)
    event = _callback(CHAT_QUESTION)
    context = _context()
    await context.set_state(ChatStates.confirm_question)
    await context.update_data(text="", file_ids=[], max_message_id="m9")

    await chat.handle_question(event, context, _db(), _user())

    assert await context.get_state() is None
    assert _edit_text(event) == "Опишите проблему"


async def test_cancel_clears_state_and_edits() -> None:
    event = _callback(CHAT_CANCEL)
    context = _context()
    await context.set_state(ChatStates.choose_ticket)
    await context.update_data(text="Привет", file_ids=[1], max_message_id="m9")

    await chat.handle_cancel(event, context)

    assert await context.get_state() is None
    assert await context.get_data() == {}
    assert _edit_text(event) == CHAT_NOT_SENT


async def test_pending_message_in_choose_state_repeats_keyboard(
    services: SimpleNamespace,
) -> None:
    services.client.list_open_tickets.return_value = [
        _ticket(TICKET_ID),
        _ticket(QUESTION_ID, TicketType.QUESTION, None),
    ]
    event = _message(text="ещё")
    context = _context()
    await context.set_state(ChatStates.choose_ticket)
    await context.update_data(text="Привет", file_ids=[], max_message_id="m9")

    await chat.handle_pending_message(event, context, _db(), _user())

    assert await context.get_state() == ChatStates.choose_ticket
    assert _last_answer_text(event) == CHAT_CHOOSE_TICKET
    rows = _answer_rows(event)
    assert [row[0].payload for row in rows] == [
        f"{CHAT_CHOOSE_PREFIX}{TICKET_ID}",
        f"{CHAT_CHOOSE_PREFIX}{QUESTION_ID}",
        CHAT_QUESTION,
        CHAT_CANCEL,
    ]
    services.message.add_client_message.assert_not_awaited()


async def test_pending_message_in_confirm_state_repeats_offer(
    services: SimpleNamespace,
) -> None:
    event = _message(text="ещё")
    context = _context()
    await context.set_state(ChatStates.confirm_question)
    await context.update_data(text="Вопрос", file_ids=[], max_message_id="m9")

    await chat.handle_pending_message(event, context, _db(), _user())

    assert await context.get_state() == ChatStates.confirm_question
    assert _last_answer_text(event) == CHAT_OFFER_QUESTION
    assert [row[0].payload for row in _answer_rows(event)] == [CHAT_QUESTION, CHAT_CANCEL]


async def test_reply_button_sets_active_ticket_and_sends_prompt(
    services: SimpleNamespace,
) -> None:
    services.client.set_active_ticket.return_value = _ticket(TICKET_ID)
    event = _callback(f"{CHAT_TICKET_PREFIX}{TICKET_ID}")
    user = _user()

    await chat.handle_reply_button(event, _context(), _db(), user)

    services.client.set_active_ticket.assert_awaited_once_with(user, TICKET_ID)
    event.ack.assert_awaited_once_with(notification=CHAT_WRITE_NOTIFICATION)
    event.send.assert_awaited_once_with(
        CHAT_WRITE_PROMPT.format(label=ticket_dative(TicketType.REQUEST, TICKET_ID))
    )
    event.edit.assert_not_awaited()


async def test_reply_button_question_label(services: SimpleNamespace) -> None:
    services.client.set_active_ticket.return_value = _ticket(QUESTION_ID, TicketType.QUESTION, None)
    event = _callback(f"{CHAT_TICKET_PREFIX}{QUESTION_ID}")

    await chat.handle_reply_button(event, _context(), _db(), _user())

    event.send.assert_awaited_once_with(
        CHAT_WRITE_PROMPT.format(label=ticket_dative(TicketType.QUESTION, QUESTION_ID))
    )


async def test_reply_button_service_error_acks_message(services: SimpleNamespace) -> None:
    message = TICKET_CLOSED_FOR_CLIENT.format(ticket_id=TICKET_ID)
    services.client.set_active_ticket.side_effect = ConflictException(message)
    event = _callback(f"{CHAT_TICKET_PREFIX}{TICKET_ID}")

    await chat.handle_reply_button(event, _context(), _db(), _user())

    event.ack.assert_awaited_once_with(notification=message)
    event.send.assert_not_awaited()


@pytest.mark.parametrize(
    "payload",
    [f"{CHAT_TICKET_PREFIX}abc", f"{CHAT_TICKET_PREFIX}0", f"{CHAT_TICKET_PREFIX}{2**63}"],
)
async def test_reply_button_bad_id_acks(services: SimpleNamespace, payload: str) -> None:
    event = _callback(payload)

    await chat.handle_reply_button(event, _context(), _db(), _user())

    event.ack.assert_awaited_once_with(notification=OUTDATED_BUTTON_TEXT)
    services.client.set_active_ticket.assert_not_awaited()
    event.send.assert_not_awaited()


async def test_reply_button_in_state_finishes_current(services: SimpleNamespace) -> None:
    event = _callback(f"{CHAT_TICKET_PREFIX}{TICKET_ID}")
    context = _context()
    await context.set_state(ChatStates.choose_ticket)

    await chat.handle_reply_button_in_state(event, context, _db(), _user())

    event.ack.assert_awaited_once_with(notification=CHAT_FINISH_CURRENT)
    services.client.set_active_ticket.assert_not_awaited()


async def test_stale_chat_callback_acks(services: SimpleNamespace) -> None:
    event = _callback("chat:unknown")

    await chat.handle_stale_callback(event)

    event.ack.assert_awaited_once_with(notification=OUTDATED_BUTTON_TEXT)
