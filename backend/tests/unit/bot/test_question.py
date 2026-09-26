from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from maxapi.context import MemoryContext
from maxapi.enums.attachment import AttachmentType
from maxapi.types import MessageCallback, MessageCreated
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.handlers import question
from src.bot.keyboards import QUESTION_CANCEL, QUESTION_WRITE
from src.bot.states import QuestionForm, RequestForm
from src.core.exceptions import AppException, MessengerException
from src.core.texts import (
    CHAT_PHOTOS_FAILED,
    DESCRIPTION_LIMIT,
    DESCRIPTION_TOO_LONG,
    FORM_PHOTOS_MAX,
    OUTDATED_BUTTON_TEXT,
    QUESTION_CANCELLED,
    QUESTION_PROMPT,
    QUESTION_SENT,
    QUESTION_TEXT_REQUIRED,
)

QUESTION_ID = 1051


def _user() -> MagicMock:
    user = MagicMock()
    user.id = 1
    user.max_user_id = 42
    return user


def _db() -> MagicMock:
    return MagicMock(spec=AsyncSession)


def _context() -> MemoryContext:
    return MemoryContext(chat_id=7, user_id=42)


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


def _message(text: str | None = None, attachments: list | None = None) -> MagicMock:
    event = MagicMock(spec=MessageCreated)
    message = MagicMock()
    message.answer = AsyncMock()
    body = MagicMock()
    body.text = text
    body.attachments = attachments or []
    message.body = body
    message.link = None
    event.message = message
    return event


def _callback(payload: str) -> MagicMock:
    event = MagicMock(spec=MessageCallback)
    event.edit = AsyncMock()
    event.ack = AsyncMock()
    callback = MagicMock()
    callback.payload = payload
    event.callback = callback
    return event


def _answer_texts(event: MagicMock) -> list[str]:
    return [call.args[0] for call in event.message.answer.await_args_list]


def _answer_rows(event: MagicMock, index: int = 0) -> list:
    return event.message.answer.await_args_list[index].kwargs["attachments"][0].payload.buttons


def _edit_text(event: MagicMock) -> str:
    return event.edit.await_args.kwargs["text"]


def _edit_rows(event: MagicMock) -> list:
    return event.edit.await_args.kwargs["attachments"][0].payload.buttons


@pytest.fixture
def service() -> MagicMock:
    svc = MagicMock()
    svc.save_photo = AsyncMock(return_value=_file(1))
    svc.create_question = AsyncMock(return_value=SimpleNamespace(id=QUESTION_ID))
    with patch("src.bot.handlers.question.ClientTicketService", return_value=svc):
        yield svc


async def test_write_clears_any_state_and_prompts(service: MagicMock) -> None:
    event = _callback(QUESTION_WRITE)
    context = _context()
    await context.set_state(RequestForm.description)
    await context.update_data(description="старое")

    await question.handle_write(event, context)

    assert await context.get_state() == QuestionForm.text
    assert await context.get_data() == {}
    assert _edit_text(event) == QUESTION_PROMPT
    assert [row[0].payload for row in _edit_rows(event)] == [QUESTION_CANCEL]


async def test_write_works_without_state(service: MagicMock) -> None:
    event = _callback(QUESTION_WRITE)
    context = _context()

    await question.handle_write(event, context)

    assert await context.get_state() == QuestionForm.text


async def test_text_only_creates_question(service: MagicMock) -> None:
    event = _message(text="  Когда отключат воду?  ")
    context = _context()
    await context.set_state(QuestionForm.text)
    user = _user()

    await question.handle_question(event, context, _db(), user)

    service.create_question.assert_awaited_once_with(
        user, description="Когда отключат воду?", photo_ids=[]
    )
    service.save_photo.assert_not_awaited()
    assert await context.get_state() is None
    assert _answer_texts(event) == [QUESTION_SENT.format(ticket_id=QUESTION_ID)]


async def test_text_with_photos_saves_them(service: MagicMock) -> None:
    service.save_photo.side_effect = [_file(11), _file(12)]
    event = _message(
        text="Смотрите фото",
        attachments=[
            _image_attachment("https://i.oneme.ru/1"),
            _image_attachment("https://i.oneme.ru/2"),
        ],
    )
    context = _context()
    await context.set_state(QuestionForm.text)

    await question.handle_question(event, context, _db(), _user())

    assert service.save_photo.await_count == 2
    assert service.create_question.await_args.kwargs["photo_ids"] == [11, 12]
    assert _answer_texts(event) == [QUESTION_SENT.format(ticket_id=QUESTION_ID)]


async def test_photos_over_limit_are_not_downloaded(service: MagicMock) -> None:
    service.save_photo.side_effect = [_file(index) for index in range(1, FORM_PHOTOS_MAX + 1)]
    event = _message(
        text="Много фото",
        attachments=[
            _image_attachment(f"https://i.oneme.ru/{index}") for index in range(FORM_PHOTOS_MAX + 3)
        ],
    )
    context = _context()
    await context.set_state(QuestionForm.text)

    await question.handle_question(event, context, _db(), _user())

    assert service.save_photo.await_count == FORM_PHOTOS_MAX
    assert len(service.create_question.await_args.kwargs["photo_ids"]) == FORM_PHOTOS_MAX


async def test_partial_photo_failure_warns(service: MagicMock) -> None:
    service.save_photo.side_effect = [_file(11), MessengerException()]
    event = _message(
        text="Текст",
        attachments=[
            _image_attachment("https://i.oneme.ru/1"),
            _image_attachment("https://i.oneme.ru/2"),
        ],
    )
    context = _context()
    await context.set_state(QuestionForm.text)

    await question.handle_question(event, context, _db(), _user())

    assert service.create_question.await_args.kwargs["photo_ids"] == [11]
    assert _answer_texts(event) == [
        QUESTION_SENT.format(ticket_id=QUESTION_ID),
        CHAT_PHOTOS_FAILED,
    ]


async def test_photo_only_asks_for_text(service: MagicMock) -> None:
    event = _message(attachments=[_image_attachment("https://i.oneme.ru/1")])
    context = _context()
    await context.set_state(QuestionForm.text)

    await question.handle_question(event, context, _db(), _user())

    service.save_photo.assert_not_awaited()
    service.create_question.assert_not_awaited()
    assert await context.get_state() == QuestionForm.text
    assert _answer_texts(event) == [QUESTION_TEXT_REQUIRED]
    assert [row[0].payload for row in _answer_rows(event)] == [QUESTION_CANCEL]


async def test_whitespace_only_asks_for_text(service: MagicMock) -> None:
    event = _message(text="   ")
    context = _context()
    await context.set_state(QuestionForm.text)

    await question.handle_question(event, context, _db(), _user())

    assert _answer_texts(event) == [QUESTION_TEXT_REQUIRED]
    assert await context.get_state() == QuestionForm.text


async def test_too_long_text_rejected_without_download(service: MagicMock) -> None:
    event = _message(
        text="a" * (DESCRIPTION_LIMIT + 1),
        attachments=[_image_attachment("https://i.oneme.ru/1")],
    )
    context = _context()
    await context.set_state(QuestionForm.text)

    await question.handle_question(event, context, _db(), _user())

    service.save_photo.assert_not_awaited()
    service.create_question.assert_not_awaited()
    assert await context.get_state() == QuestionForm.text
    assert _answer_texts(event) == [DESCRIPTION_TOO_LONG]
    assert [row[0].payload for row in _answer_rows(event)] == [QUESTION_CANCEL]


async def test_unsupported_attachment_only_asks_for_text(service: MagicMock) -> None:
    event = _message(attachments=[_sticker_attachment()])
    context = _context()
    await context.set_state(QuestionForm.text)

    await question.handle_question(event, context, _db(), _user())

    assert _answer_texts(event) == [QUESTION_TEXT_REQUIRED]


async def test_service_error_stays_in_state(service: MagicMock) -> None:
    service.create_question.side_effect = AppException("Опишите проблему", status_code=400)
    event = _message(text="Вопрос")
    context = _context()
    await context.set_state(QuestionForm.text)

    await question.handle_question(event, context, _db(), _user())

    assert await context.get_state() == QuestionForm.text
    assert _answer_texts(event) == ["Опишите проблему"]
    assert [row[0].payload for row in _answer_rows(event)] == [QUESTION_CANCEL]


async def test_cancel_clears_state_and_shows_menu() -> None:
    event = _callback(QUESTION_CANCEL)
    context = _context()
    await context.set_state(QuestionForm.text)

    await question.handle_cancel(event, context)

    assert await context.get_state() is None
    assert _edit_text(event) == QUESTION_CANCELLED
    assert _edit_rows(event)[0][0].payload == "form:start"


async def test_callback_without_original_message_acks() -> None:
    event = _callback(QUESTION_WRITE)
    event.edit = AsyncMock(side_effect=ValueError("message is gone"))
    context = _context()

    await question.handle_write(event, context)

    event.ack.assert_awaited_once_with(notification=OUTDATED_BUTTON_TEXT)


async def test_stale_question_callback_acks() -> None:
    event = _callback("question:unknown")

    await question.handle_stale_callback(event)

    event.ack.assert_awaited_once_with(notification=OUTDATED_BUTTON_TEXT)
    event.edit.assert_not_awaited()
