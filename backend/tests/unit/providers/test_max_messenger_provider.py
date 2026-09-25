from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from aiohttp import ClientConnectionError
from maxapi.enums.parse_mode import ParseMode
from maxapi.enums.upload_type import UploadType
from maxapi.exceptions import MaxApiError
from maxapi.types.attachments.buttons.attachment_button import AttachmentButton
from maxapi.types.attachments.buttons.callback_button import CallbackButton
from maxapi.types.attachments.buttons.link_button import LinkButton
from maxapi.types.attachments.buttons.open_app_button import OpenAppButton
from maxapi.types.attachments.upload import AttachmentUpload

from src.core.constants import ButtonType
from src.core.exceptions import AppException, MessengerException
from src.providers.max_messenger_provider import MaxMessengerProvider
from src.providers.messenger_provider import Button, OutgoingFile


def _sended_message(mid: str = "mid-1") -> SimpleNamespace:
    return SimpleNamespace(message=SimpleNamespace(body=SimpleNamespace(mid=mid)))


@pytest.fixture
def bot():
    with patch("src.providers.max_messenger_provider.Bot") as bot_cls:
        instance = bot_cls.return_value
        instance.send_message = AsyncMock(return_value=_sended_message())
        instance.edit_message = AsyncMock(return_value=SimpleNamespace(success=True))
        instance.get_me = AsyncMock(return_value=SimpleNamespace(username="uk_bot"))
        instance.upload_media = AsyncMock(
            return_value=SimpleNamespace(payload=SimpleNamespace(token="token-1"))
        )
        instance.close_session = AsyncMock()
        yield instance


@pytest.fixture
def provider(bot):
    return MaxMessengerProvider("bot-token")


def _provider_with_transport(handler) -> MaxMessengerProvider:
    return MaxMessengerProvider("bot-token", http_transport=httpx.MockTransport(handler))


async def test_send_plain_text(bot, provider):
    mid = await provider.send_message(10, "hello")

    assert mid == "mid-1"
    bot.send_message.assert_awaited_once_with(
        user_id=10, text="hello", attachments=None, format=None
    )


async def test_send_maps_button_types_and_keeps_rows(bot, provider):
    buttons = [
        [Button(text="Callback", type=ButtonType.CALLBACK, payload="cb-1")],
        [
            Button(text="Link", type=ButtonType.LINK, payload="https://example.com"),
            Button(text="Open", type=ButtonType.OPEN_APP, payload="ticket-1"),
        ],
    ]

    await provider.send_message(10, "hello", buttons=buttons)

    attachments = bot.send_message.call_args.kwargs["attachments"]
    assert len(attachments) == 1
    keyboard = attachments[0]
    assert isinstance(keyboard, AttachmentButton)
    row1, row2 = keyboard.payload.buttons
    assert len(row1) == 1
    assert len(row2) == 2

    assert isinstance(row1[0], CallbackButton)
    assert row1[0].text == "Callback"
    assert row1[0].payload == "cb-1"

    assert isinstance(row2[0], LinkButton)
    assert row2[0].text == "Link"
    assert row2[0].url == "https://example.com"

    assert isinstance(row2[1], OpenAppButton)
    assert row2[1].text == "Open"
    assert row2[1].web_app == "uk_bot"
    assert row2[1].payload == "ticket-1"


async def test_send_maps_plain_string_button_type(bot, provider):
    buttons = [[Button(text="Callback", type="CALLBACK", payload="cb-1")]]

    await provider.send_message(1, "hello", buttons=buttons)

    keyboard = bot.send_message.call_args.kwargs["attachments"][0]
    assert isinstance(keyboard.payload.buttons[0][0], CallbackButton)


async def test_open_app_resolves_bot_username_once(bot, provider):
    button = Button(text="Open", type=ButtonType.OPEN_APP, payload="ticket-1")

    await provider.send_message(1, "first", buttons=[[button]])
    await provider.send_message(2, "second", buttons=[[button]])

    bot.get_me.assert_awaited_once()


async def test_files_are_sent_before_keyboard_with_upload_types(bot, provider):
    files = [
        OutgoingFile(token="img-token", mime="image/png"),
        OutgoingFile(token="doc-token", mime="application/pdf"),
    ]
    buttons = [[Button(text="Open", type=ButtonType.OPEN_APP, payload="ticket-1")]]

    await provider.send_message(1, "text", buttons=buttons, files=files)

    attachments = bot.send_message.call_args.kwargs["attachments"]
    assert isinstance(attachments[0], AttachmentUpload)
    assert attachments[0].type == UploadType.IMAGE
    assert attachments[0].payload.token == "img-token"
    assert isinstance(attachments[1], AttachmentUpload)
    assert attachments[1].type == UploadType.FILE
    assert attachments[1].payload.token == "doc-token"
    assert isinstance(attachments[2], AttachmentButton)


async def test_send_markdown_sets_parse_mode(bot, provider):
    await provider.send_message(1, "**bold**", markdown=True)

    assert bot.send_message.call_args.kwargs["format"] == ParseMode.MARKDOWN


async def test_edit_without_buttons_clears_keyboard(bot, provider):
    await provider.edit_message("mid-1", "new text")

    bot.edit_message.assert_awaited_once_with(
        message_id="mid-1", text="new text", attachments=[], format=None
    )


async def test_edit_with_buttons_and_markdown(bot, provider):
    buttons = [[Button(text="Open", type=ButtonType.OPEN_APP, payload="ticket-1")]]

    await provider.edit_message("mid-1", "new text", buttons=buttons, markdown=True)

    kwargs = bot.edit_message.call_args.kwargs
    assert kwargs["format"] == ParseMode.MARKDOWN
    attachments = kwargs["attachments"]
    assert len(attachments) == 1
    assert isinstance(attachments[0], AttachmentButton)
    assert isinstance(attachments[0].payload.buttons[0][0], OpenAppButton)


async def test_edit_failure_raises_messenger_exception(bot, provider):
    bot.edit_message.return_value = SimpleNamespace(success=False)

    with pytest.raises(MessengerException):
        await provider.edit_message("mid-1", "text")


async def test_upload_file_returns_token(bot, provider):
    token = await provider.upload_file(b"png", "image/png", filename="a.png")

    assert token == "token-1"
    media = bot.upload_media.call_args.args[0]
    assert media.type == UploadType.IMAGE
    assert media.filename == "a.png"
    assert media.buffer == b"png"


async def test_upload_file_non_image_uses_file_type(bot, provider):
    await provider.upload_file(b"pdf", "application/pdf")

    media = bot.upload_media.call_args.args[0]
    assert media.type == UploadType.FILE


@pytest.mark.parametrize(
    "error",
    [
        MaxApiError(code=500, raw={"error": "boom"}),
        ClientConnectionError("no network"),
        TimeoutError(),
        RuntimeError("Не удалось отправить сообщение"),
    ],
)
async def test_send_errors_become_messenger_exception(bot, provider, error):
    bot.send_message.side_effect = error

    with pytest.raises(MessengerException):
        await provider.send_message(1, "text")


async def test_edit_runtime_error_becomes_messenger_exception(bot, provider):
    bot.edit_message.side_effect = RuntimeError("Не удалось отредактировать сообщение")

    with pytest.raises(MessengerException):
        await provider.edit_message("mid-1", "text")


async def test_download_file_streams_bytes_and_strips_mime_parameters():
    def handler(request):
        return httpx.Response(
            200, content=b"image-bytes", headers={"Content-Type": "image/webp; charset=x"}
        )

    provider = _provider_with_transport(handler)
    data, mime = await provider.download_file("https://i.oneme.ru/i?r=abc", 100)

    assert data == b"image-bytes"
    assert mime == "image/webp"
    await provider.close()


async def test_download_file_defaults_mime_to_octet_stream():
    def handler(request):
        return httpx.Response(200, content=b"data")

    provider = _provider_with_transport(handler)
    data, mime = await provider.download_file("https://i.oneme.ru/i?r=abc", 100)

    assert data == b"data"
    assert mime == "application/octet-stream"


async def test_download_file_non_2xx_raises():
    def handler(request):
        return httpx.Response(404, content=b"nope")

    provider = _provider_with_transport(handler)

    with pytest.raises(MessengerException):
        await provider.download_file("https://i.oneme.ru/i?r=abc", 100)


async def test_download_file_content_length_over_limit_raises_413():
    def handler(request):
        return httpx.Response(200, content=b"0123456789", headers={"Content-Length": "10"})

    provider = _provider_with_transport(handler)

    with pytest.raises(AppException) as exc_info:
        await provider.download_file("https://i.oneme.ru/i?r=abc", 5)

    assert exc_info.value.status_code == 413
    assert exc_info.value.message == "Файл слишком большой"


async def test_download_file_body_over_limit_without_content_length_raises_413():
    def handler(request):
        async def body():
            yield b"a" * 10

        return httpx.Response(200, content=body())

    provider = _provider_with_transport(handler)

    with pytest.raises(AppException) as exc_info:
        await provider.download_file("https://i.oneme.ru/i?r=abc", 5)

    assert exc_info.value.status_code == 413


async def test_download_file_rejects_https_to_http_redirect():
    requested = []

    def handler(request):
        requested.append(request.url.scheme)
        if request.url.scheme == "https":
            return httpx.Response(302, headers={"Location": "http://i.oneme.ru/downgraded"})
        return httpx.Response(200, content=b"data")

    provider = _provider_with_transport(handler)

    with pytest.raises(MessengerException):
        await provider.download_file("https://i.oneme.ru/i?r=abc", 100)

    assert requested == ["https", "http"]


async def test_download_file_rejects_non_https_without_request():
    requested = []

    def handler(request):
        requested.append(request)
        return httpx.Response(200, content=b"data")

    provider = _provider_with_transport(handler)

    with pytest.raises(MessengerException):
        await provider.download_file("http://i.oneme.ru/i?r=abc", 100)

    assert requested == []


async def test_download_file_sends_no_authorization_header():
    captured = {}

    def handler(request):
        captured["headers"] = request.headers
        return httpx.Response(200, content=b"data")

    provider = _provider_with_transport(handler)
    await provider.download_file("https://i.oneme.ru/i?r=abc", 100)

    assert "authorization" not in captured["headers"]


async def test_close_closes_bot_session(bot, provider):
    await provider.close()

    bot.close_session.assert_awaited_once()
