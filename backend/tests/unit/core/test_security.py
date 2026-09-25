import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qsl, urlencode

import pytest

from src.core.exceptions import UnauthorizedException
from src.core.security import validate_init_data

BOT_TOKEN = "test-bot-token"


def _sign(fields: dict[str, str], bot_token: str = BOT_TOKEN) -> str:
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    signed = {
        **fields,
        "hash": hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest(),
    }
    return urlencode(signed)


def _fields(max_user_id: int = 42, auth_date: datetime | None = None) -> dict[str, str]:
    return {
        "auth_date": str(int((auth_date or datetime.now(UTC)).timestamp())),
        "query_id": "AAA",
        "user": json.dumps(
            {
                "id": max_user_id,
                "first_name": "Иван",
                "last_name": "Петров",
                "username": "ivan",
            },
            ensure_ascii=False,
        ),
    }


def test_valid_init_data_returns_user():
    init_data = _sign(_fields(max_user_id=42))

    result = validate_init_data(init_data, BOT_TOKEN, datetime.now(UTC))

    assert result.max_user_id == 42
    assert result.first_name == "Иван"
    assert result.last_name == "Петров"
    assert result.username == "ivan"


def test_tampered_payload_is_rejected():
    fields = _fields(max_user_id=1)
    init_data = _sign(fields)
    signature = dict(parse_qsl(init_data))["hash"]
    fields["user"] = json.dumps({"id": 2, "first_name": "Хак"}, ensure_ascii=False)
    tampered = urlencode({**fields, "hash": signature})

    with pytest.raises(UnauthorizedException):
        validate_init_data(tampered, BOT_TOKEN, datetime.now(UTC))


def test_wrong_bot_token_is_rejected():
    init_data = _sign(_fields(), bot_token="wrong-token")

    with pytest.raises(UnauthorizedException):
        validate_init_data(init_data, BOT_TOKEN, datetime.now(UTC))


def test_expired_auth_date_is_rejected():
    old = datetime.now(UTC) - timedelta(hours=25)
    init_data = _sign(_fields(auth_date=old))

    with pytest.raises(UnauthorizedException):
        validate_init_data(init_data, BOT_TOKEN, datetime.now(UTC))


def test_missing_user_is_rejected():
    fields = _fields()
    del fields["user"]

    with pytest.raises(UnauthorizedException):
        validate_init_data(_sign(fields), BOT_TOKEN, datetime.now(UTC))


def test_missing_hash_is_rejected():
    init_data = urlencode(_fields())

    with pytest.raises(UnauthorizedException):
        validate_init_data(init_data, BOT_TOKEN, datetime.now(UTC))


def test_non_ascii_hash_is_rejected():
    init_data = urlencode({**_fields(), "hash": "абв"})

    with pytest.raises(UnauthorizedException):
        validate_init_data(init_data, BOT_TOKEN, datetime.now(UTC))


def test_invalid_json_user_is_rejected():
    init_data = _sign({**_fields(), "user": "{not json}"})

    with pytest.raises(UnauthorizedException):
        validate_init_data(init_data, BOT_TOKEN, datetime.now(UTC))


def test_non_object_json_user_is_rejected():
    init_data = _sign({**_fields(), "user": "[]"})

    with pytest.raises(UnauthorizedException):
        validate_init_data(init_data, BOT_TOKEN, datetime.now(UTC))


def test_future_auth_date_within_skew_is_allowed():
    future = datetime.now(UTC) + timedelta(minutes=1)
    init_data = _sign(_fields(auth_date=future))

    result = validate_init_data(init_data, BOT_TOKEN, datetime.now(UTC))

    assert result.max_user_id == 42


def test_future_auth_date_beyond_skew_is_rejected():
    future = datetime.now(UTC) + timedelta(minutes=10)
    init_data = _sign(_fields(auth_date=future))

    with pytest.raises(UnauthorizedException):
        validate_init_data(init_data, BOT_TOKEN, datetime.now(UTC))


def test_overflowing_auth_date_is_rejected():
    init_data = _sign({**_fields(), "auth_date": "99999999999999999999"})

    with pytest.raises(UnauthorizedException):
        validate_init_data(init_data, BOT_TOKEN, datetime.now(UTC))


def test_empty_bot_token_is_rejected():
    init_data = _sign(_fields())

    with pytest.raises(UnauthorizedException):
        validate_init_data(init_data, "", datetime.now(UTC))
