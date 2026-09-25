import logging

from src.core.exceptions import MessengerException
from src.providers.messenger_provider import Button, MessengerProvider, OutgoingFile

logger = logging.getLogger(__name__)


class NoopMessengerProvider(MessengerProvider):
    async def send_message(
        self,
        user_id: int,
        text: str,
        *,
        buttons: list[list[Button]] | None = None,
        files: list[OutgoingFile] | None = None,
        markdown: bool = False,
    ) -> str | None:
        logger.info(
            "Messenger disabled: skip sending to user %s (%d buttons, %d files)",
            user_id,
            sum(len(row) for row in buttons or []),
            len(files or []),
        )
        return None

    async def edit_message(
        self,
        message_id: str,
        text: str,
        *,
        buttons: list[list[Button]] | None = None,
        markdown: bool = False,
    ) -> None:
        logger.info(
            "Messenger disabled: skip editing message %s (%d buttons)",
            message_id,
            sum(len(row) for row in buttons or []),
        )

    async def upload_file(self, data: bytes, mime: str, filename: str | None = None) -> str | None:
        logger.info(
            "Messenger disabled: skip uploading a %s file (%d bytes)",
            mime,
            len(data),
        )
        return None

    async def download_file(self, url: str, max_size: int) -> tuple[bytes, str]:
        raise MessengerException()

    async def close(self) -> None:
        return None
