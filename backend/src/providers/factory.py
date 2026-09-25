from src.core.config import settings
from src.providers.local_storage_provider import LocalStorageProvider
from src.providers.storage_provider import StorageProvider

_storage_provider: StorageProvider | None = None


def get_storage_provider() -> StorageProvider:
    global _storage_provider
    if _storage_provider is None:
        _storage_provider = LocalStorageProvider(settings.storage_dir)
    return _storage_provider
