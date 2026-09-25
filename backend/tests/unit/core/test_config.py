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


def test_admin_max_user_ids_parses_comma_separated():
    settings = _make_settings(admin_max_user_ids="185257313,42")

    assert settings.admin_max_user_ids == [185257313, 42]


def test_admin_max_user_ids_empty_string_is_empty_list():
    settings = _make_settings(admin_max_user_ids="")

    assert settings.admin_max_user_ids == []


def test_admin_max_user_ids_defaults_to_empty_list():
    settings = _make_settings()

    assert settings.admin_max_user_ids == []
