from src.core.config import settings
from src.providers.local_storage_provider import LocalStorageProvider
from src.providers.max_messenger_provider import MaxMessengerProvider
from src.providers.messenger_provider import MessengerProvider
from src.providers.noop_messenger_provider import NoopMessengerProvider
from src.providers.storage_provider import StorageProvider

_storage_provider: StorageProvider | None = None
_messenger_provider: MessengerProvider | None = None


def get_storage_provider() -> StorageProvider:
    global _storage_provider
    if _storage_provider is None:
        _storage_provider = LocalStorageProvider(settings.storage_dir)
    return _storage_provider


def get_messenger_provider() -> MessengerProvider:
    global _messenger_provider
    if _messenger_provider is None:
        if settings.bot_mode == "off":
            _messenger_provider = NoopMessengerProvider()
        else:
            _messenger_provider = MaxMessengerProvider(settings.bot_token)
    return _messenger_provider


async def close_messenger_provider() -> None:
    global _messenger_provider
    if _messenger_provider is not None:
        await _messenger_provider.close()
        _messenger_provider = None
