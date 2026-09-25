import pytest
from pydantic import ValidationError

from src.core.config import Settings


def _make_settings(**overrides) -> Settings:
    return Settings(
        _env_file=None,
        database_user="uk",
        database_password="uk",
        database_name="uk_support",
        **overrides,
    )


def test_polling_without_token_raises():
    with pytest.raises(ValidationError, match="BOT_TOKEN"):
        _make_settings(bot_mode="polling", bot_token="")


def test_off_without_token_is_allowed():
    settings = _make_settings(bot_mode="off", bot_token="")

    assert settings.bot_mode == "off"
    assert settings.bot_token == ""
