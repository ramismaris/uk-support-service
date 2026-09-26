from maxapi.enums.attachment import AttachmentType
from maxapi.enums.message_link_type import MessageLinkType
from maxapi.filters import F

from src.core.constants import BIGINT_MAX

# Commands are never treated as free input: /start must reach the menu and reset any state.
NOT_A_COMMAND = ~F.message.body.text.regexp(r"^/")


def parse_id(payload: str, prefix: str) -> int | None:
    if not payload.startswith(prefix):
        return None
    raw = payload[len(prefix) :]
    if not raw.isascii() or not raw.isdigit():
        return None
    value = int(raw)
    if 1 <= value <= BIGINT_MAX:
        return value
    return None


def _is_forward(message) -> bool:
    return message.link is not None and message.link.type == MessageLinkType.FORWARD


def attachments(message) -> list:
    items: list = []
    if message.body is not None and message.body.attachments:
        items.extend(message.body.attachments)
    if _is_forward(message) and message.link.message.attachments:
        items.extend(message.link.message.attachments)
    return items


def image_urls(message) -> list[str]:
    urls: list[str] = []
    for attachment in attachments(message):
        if attachment.type != AttachmentType.IMAGE:
            continue
        url = getattr(attachment.payload, "url", None)
        if url:
            urls.append(url)
    return urls


def message_text(message) -> str:
    own = ""
    if message.body is not None and message.body.text is not None:
        own = message.body.text.strip()
    if own:
        return own
    if not _is_forward(message) or message.link.message.text is None:
        return ""
    return message.link.message.text.strip()
