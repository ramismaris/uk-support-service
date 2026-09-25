import logging

import httpx
from aiohttp import ClientError
from maxapi import Bot
from maxapi.client.default import DefaultConnectionProperties
from maxapi.enums.parse_mode import ParseMode
from maxapi.enums.upload_type import UploadType
from maxapi.exceptions import MaxError
from maxapi.types.attachments.attachment import Attachment
from maxapi.types.attachments.buttons.attachment_button import AttachmentButton
from maxapi.types.attachments.buttons.callback_button import CallbackButton
from maxapi.types.attachments.buttons.link_button import LinkButton
from maxapi.types.attachments.buttons.open_app_button import OpenAppButton
from maxapi.types.attachments.upload import AttachmentPayload, AttachmentUpload
from maxapi.types.input_media import InputMediaBuffer
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from src.core.constants import ButtonType
from src.core.exceptions import AppException, MessengerException
from src.providers.messenger_provider import Button, MessengerProvider, OutgoingFile

logger = logging.getLogger(__name__)

_MESSENGER_ERRORS = (MaxError, ClientError, TimeoutError, httpx.HTTPError)
_MESSAGE_ERRORS = (*_MESSENGER_ERRORS, RuntimeError)


def _log_failure(method: str, exc: BaseException) -> None:
    logger.warning("Max %s failed: %s", method, type(exc).__name__)


class MaxMessengerProvider(MessengerProvider):
    def __init__(self, token: str, http_transport: httpx.AsyncBaseTransport | None = None):
        self._bot = Bot(
            token=token,
            default_connection=DefaultConnectionProperties(timeout=60, sock_connect=10),
        )
        self._http_transport = http_transport
        self._http: httpx.AsyncClient | None = None
        self._bot_username: str | None = None

    async def send_message(
        self,
        user_id: int,
        text: str,
        *,
        buttons: list[list[Button]] | None = None,
        files: list[OutgoingFile] | None = None,
        markdown: bool = False,
    ) -> str | None:
        try:
            attachments = await self._build_attachments(buttons, files)
            result = await self._bot.send_message(
                user_id=user_id,
                text=text,
                attachments=attachments or None,
                format=ParseMode.MARKDOWN if markdown else None,
            )
        except _MESSAGE_ERRORS as exc:
            _log_failure("send_message", exc)
            raise MessengerException() from exc
        return result.message.body.mid

    async def edit_message(
        self,
        message_id: str,
        text: str,
        *,
        buttons: list[list[Button]] | None = None,
        markdown: bool = False,
    ) -> None:
        try:
            attachments = await self._build_attachments(buttons, None)
            result = await self._bot.edit_message(
                message_id=message_id,
                text=text,
                attachments=attachments,
                format=ParseMode.MARKDOWN if markdown else None,
            )
        except _MESSAGE_ERRORS as exc:
            _log_failure("edit_message", exc)
            raise MessengerException() from exc
        if not result.success:
            raise MessengerException()

    async def upload_file(self, data: bytes, mime: str, filename: str | None = None) -> str | None:
        try:
            media = InputMediaBuffer(data, filename=filename, type=self._upload_type(mime))
            result = await self._bot.upload_media(media)
        except _MESSENGER_ERRORS as exc:
            _log_failure("upload_file", exc)
            raise MessengerException() from exc
        return result.payload.token

    async def download_file(self, url: str, max_size: int) -> tuple[bytes, str]:
        if not url.startswith("https://"):
            raise MessengerException()

        client = self._get_http_client()
        try:
            async with client.stream("GET", url) as response:
                if response.url.scheme != "https":
                    raise MessengerException()

                if not 200 <= response.status_code < 300:
                    raise MessengerException()

                content_length = response.headers.get("Content-Length")
                if content_length is not None and int(content_length) > max_size:
                    raise AppException("Файл слишком большой", status_code=413)

                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > max_size:
                        raise AppException("Файл слишком большой", status_code=413)

                content_type = response.headers.get("Content-Type")
        except _MESSENGER_ERRORS as exc:
            _log_failure("download_file", exc)
            raise MessengerException() from exc

        mime = content_type.split(";", 1)[0].strip() if content_type else ""
        return bytes(body), mime or "application/octet-stream"

    async def close(self) -> None:
        await self._bot.close_session()
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    async def _build_attachments(
        self,
        buttons: list[list[Button]] | None,
        files: list[OutgoingFile] | None,
    ) -> list[Attachment | AttachmentButton | AttachmentUpload]:
        attachments: list[Attachment | AttachmentButton | AttachmentUpload] = [
            self._to_attachment(file) for file in files or []
        ]
        if buttons:
            keyboard = InlineKeyboardBuilder()
            for row in buttons:
                keyboard.row(*[await self._to_button(button) for button in row])
            attachments.append(keyboard.as_markup())
        return attachments

    @staticmethod
    def _to_attachment(file: OutgoingFile) -> AttachmentUpload:
        return AttachmentUpload(
            type=MaxMessengerProvider._upload_type(file.mime),
            payload=AttachmentPayload(token=file.token),
        )

    async def _to_button(self, button: Button) -> CallbackButton | LinkButton | OpenAppButton:
        if button.type == ButtonType.CALLBACK:
            return CallbackButton(text=button.text, payload=button.payload)
        if button.type == ButtonType.LINK:
            return LinkButton(text=button.text, url=button.payload)
        return OpenAppButton(
            text=button.text,
            web_app=await self._get_bot_username(),
            payload=button.payload,
        )

    async def _get_bot_username(self) -> str:
        if self._bot_username is None:
            user = await self._bot.get_me()
            self._bot_username = user.username or ""
        return self._bot_username

    @staticmethod
    def _upload_type(mime: str) -> UploadType:
        return UploadType.IMAGE if mime.startswith("image/") else UploadType.FILE

    def _get_http_client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(
                timeout=30,
                follow_redirects=True,
                transport=self._http_transport,
            )
        return self._http
