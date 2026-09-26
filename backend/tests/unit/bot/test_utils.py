from unittest.mock import MagicMock

from maxapi.enums.attachment import AttachmentType
from maxapi.enums.message_link_type import MessageLinkType

from src.bot.utils import image_urls, message_text


def _image_attachment(url: str) -> MagicMock:
    attachment = MagicMock()
    attachment.type = AttachmentType.IMAGE
    attachment.payload.url = url
    return attachment


def _message(
    text: str | None = None,
    attachments: list | None = None,
    *,
    link_type: MessageLinkType | None = None,
    link_text: str | None = None,
    link_attachments: list | None = None,
) -> MagicMock:
    message = MagicMock()
    body = MagicMock()
    body.text = text
    body.attachments = attachments or []
    message.body = body
    if link_type is not None:
        link = MagicMock()
        link.type = link_type
        link.message.text = link_text
        link.message.attachments = link_attachments or []
        message.link = link
    else:
        message.link = None
    return message


def test_reply_does_not_take_quoted_attachments() -> None:
    message = _message(
        text="ответ",
        link_type=MessageLinkType.REPLY,
        link_attachments=[_image_attachment("https://i.oneme.ru/staff")],
    )

    assert image_urls(message) == []


def test_forward_takes_attachments() -> None:
    message = _message(
        link_type=MessageLinkType.FORWARD,
        link_attachments=[_image_attachment("https://i.oneme.ru/fwd")],
    )

    assert image_urls(message) == ["https://i.oneme.ru/fwd"]


def test_forward_text_is_used_without_own_text() -> None:
    message = _message(
        link_type=MessageLinkType.FORWARD,
        link_text="  пересланный текст  ",
    )

    assert message_text(message) == "пересланный текст"


def test_own_text_wins_over_forwarded() -> None:
    message = _message(
        text="  свой текст  ",
        link_type=MessageLinkType.FORWARD,
        link_text="пересланный текст",
    )

    assert message_text(message) == "свой текст"


def test_reply_text_is_not_used_without_own_text() -> None:
    message = _message(
        link_type=MessageLinkType.REPLY,
        link_text="цитата",
    )

    assert message_text(message) == ""
