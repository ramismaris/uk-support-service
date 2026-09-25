import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qsl

from src.core.exceptions import UnauthorizedException

INIT_DATA_MAX_AGE = timedelta(hours=24)
INIT_DATA_CLOCK_SKEW = timedelta(minutes=5)

_HASH_LENGTH = 64
_HEX_DIGITS = frozenset("0123456789abcdef")


@dataclass(frozen=True)
class MaxInitData:
    max_user_id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _is_valid_hash(value: str) -> bool:
    return len(value) == _HASH_LENGTH and all(char in _HEX_DIGITS for char in value)


def validate_init_data(init_data: str, bot_token: str, now: datetime) -> MaxInitData:
    if not bot_token:
        raise UnauthorizedException("Не удалось проверить данные входа")

    pairs = parse_qsl(init_data, keep_blank_values=True)
    fields = dict(pairs)

    received_hash = fields.get("hash")
    if not received_hash or not _is_valid_hash(received_hash):
        raise UnauthorizedException("Не удалось проверить данные входа")

    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(pair for pair in pairs if pair[0] != "hash")
    )
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_hash.encode(), received_hash.encode()):
        raise UnauthorizedException("Не удалось проверить данные входа")

    raw_user = fields.get("user")
    if not raw_user:
        raise UnauthorizedException("Не удалось проверить данные входа")
    try:
        user = json.loads(raw_user)
        max_user_id = int(user["id"])
        first_name = user["first_name"]
    except (ValueError, KeyError, TypeError):
        raise UnauthorizedException("Не удалось проверить данные входа")

    raw_auth_date = fields.get("auth_date")
    try:
        auth_date = datetime.fromtimestamp(int(raw_auth_date), tz=UTC)
    except (ValueError, TypeError, OSError, OverflowError):
        raise UnauthorizedException("Не удалось проверить данные входа")
    if now - auth_date > INIT_DATA_MAX_AGE:
        raise UnauthorizedException("Данные входа устарели")
    if auth_date - now > INIT_DATA_CLOCK_SKEW:
        raise UnauthorizedException("Не удалось проверить данные входа")

    return MaxInitData(
        max_user_id=max_user_id,
        first_name=first_name,
        last_name=user.get("last_name"),
        username=user.get("username"),
    )
