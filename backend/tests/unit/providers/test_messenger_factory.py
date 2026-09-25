from unittest.mock import AsyncMock, patch

import pytest

from src.providers import factory
from src.providers.max_messenger_provider import MaxMessengerProvider
from src.providers.messenger_provider import MessengerProvider
from src.providers.noop_messenger_provider import NoopMessengerProvider


@pytest.fixture(autouse=True)
def reset_messenger_provider():
    factory._messenger_provider = None
    yield
    factory._messenger_provider = None


def test_off_mode_returns_noop(monkeypatch):
    monkeypatch.setattr(factory.settings, "bot_mode", "off")

    assert isinstance(factory.get_messenger_provider(), NoopMessengerProvider)


def test_polling_mode_returns_max_and_caches(monkeypatch):
    monkeypatch.setattr(factory.settings, "bot_mode", "polling")
    monkeypatch.setattr(factory.settings, "bot_token", "token")

    with patch("src.providers.max_messenger_provider.Bot") as bot_cls:
        provider = factory.get_messenger_provider()
        cached = factory.get_messenger_provider()

    assert isinstance(provider, MaxMessengerProvider)
    assert cached is provider
    bot_cls.assert_called_once()


async def test_close_messenger_provider_closes_and_resets():
    provider = AsyncMock(spec=MessengerProvider)
    factory._messenger_provider = provider

    await factory.close_messenger_provider()

    provider.close.assert_awaited_once()
    assert factory._messenger_provider is None


async def test_close_messenger_provider_without_instance_is_noop():
    await factory.close_messenger_provider()

    assert factory._messenger_provider is None
