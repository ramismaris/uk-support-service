from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.core.constants import ButtonType


@dataclass(frozen=True)
class Button:
    text: str
    type: ButtonType
    payload: str


@dataclass(frozen=True)
class OutgoingFile:
    token: str
    mime: str


class MessengerProvider(ABC):
    @abstractmethod
    async def send_message(
        self,
        user_id: int,
        text: str,
        *,
        buttons: list[list[Button]] | None = None,
        files: list[OutgoingFile] | None = None,
        markdown: bool = False,
    ) -> str | None: ...

    @abstractmethod
    async def edit_message(
        self,
        message_id: str,
        text: str,
        *,
        buttons: list[list[Button]] | None = None,
        markdown: bool = False,
    ) -> None: ...

    @abstractmethod
    async def upload_file(
        self, data: bytes, mime: str, filename: str | None = None
    ) -> str | None: ...

    @abstractmethod
    async def download_file(self, url: str, max_size: int) -> tuple[bytes, str]: ...

    @abstractmethod
    async def close(self) -> None: ...
