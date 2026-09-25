import pytest

from src.core.constants import ButtonType
from src.core.exceptions import MessengerException
from src.providers.messenger_provider import Button, OutgoingFile
from src.providers.noop_messenger_provider import NoopMessengerProvider


async def test_send_message_returns_none():
    result = await NoopMessengerProvider().send_message(
        10,
        "text",
        buttons=[[Button(text="a", type=ButtonType.LINK, payload="https://example.com")]],
        files=[OutgoingFile(token="t", mime="image/png")],
        markdown=True,
    )

    assert result is None


async def test_edit_message_returns_none():
    result = await NoopMessengerProvider().edit_message("mid-1", "text")

    assert result is None


async def test_upload_file_returns_none():
    result = await NoopMessengerProvider().upload_file(b"data", "image/png")

    assert result is None


async def test_download_file_raises_messenger_exception():
    with pytest.raises(MessengerException):
        await NoopMessengerProvider().download_file("https://i.oneme.ru/i?r=abc", 100)


async def test_close_returns_none():
    assert await NoopMessengerProvider().close() is None
