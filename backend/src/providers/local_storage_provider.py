import asyncio
from pathlib import Path

from src.providers.storage_provider import StorageProvider


class LocalStorageProvider(StorageProvider):
    def __init__(self, storage_dir: str):
        self._root = Path(storage_dir)

    def _resolve(self, key: str) -> Path:
        path = Path(key)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"Invalid storage key: {key}")
        root = self._root.resolve()
        if not (root / path).resolve().is_relative_to(root):
            raise ValueError(f"Invalid storage key: {key}")
        return self._root / path

    async def save(self, key: str, data: bytes) -> None:
        path = self._resolve(key)
        await asyncio.to_thread(self._write, path, data)

    async def read(self, key: str) -> bytes:
        path = self._resolve(key)
        return await asyncio.to_thread(path.read_bytes)

    async def delete(self, key: str) -> None:
        path = self._resolve(key)
        await asyncio.to_thread(path.unlink, missing_ok=True)

    @staticmethod
    def _write(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
