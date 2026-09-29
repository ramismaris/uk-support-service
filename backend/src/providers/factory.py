from src.core.config import settings
from src.providers.llm_provider import LlmProvider
from src.providers.local_storage_provider import LocalStorageProvider
from src.providers.max_messenger_provider import MaxMessengerProvider
from src.providers.messenger_provider import MessengerProvider
from src.providers.noop_messenger_provider import NoopMessengerProvider
from src.providers.openai_compatible_llm_provider import OpenAiCompatibleLlmProvider
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


def get_llm_provider() -> LlmProvider | None:
    if not settings.llm_base_url or not settings.llm_model:
        return None
    return OpenAiCompatibleLlmProvider(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        timeout_seconds=settings.llm_timeout_seconds,
        extra_headers=settings.llm_extra_headers,
    )
