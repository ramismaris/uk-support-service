import pytest

from src.providers.local_storage_provider import LocalStorageProvider


async def test_save_read_delete_round_trip(tmp_path):
    provider = LocalStorageProvider(str(tmp_path))

    await provider.save("a.bin", b"data")
    assert await provider.read("a.bin") == b"data"

    await provider.delete("a.bin")
    with pytest.raises(FileNotFoundError):
        await provider.read("a.bin")


async def test_nested_key_creates_parent_directories(tmp_path):
    provider = LocalStorageProvider(str(tmp_path))

    await provider.save("files/2026/01/x.bin", b"nested")

    assert (tmp_path / "files/2026/01/x.bin").read_bytes() == b"nested"


async def test_read_missing_key_raises(tmp_path):
    provider = LocalStorageProvider(str(tmp_path))

    with pytest.raises(FileNotFoundError):
        await provider.read("missing.bin")


async def test_absolute_key_is_rejected(tmp_path):
    provider = LocalStorageProvider(str(tmp_path))

    with pytest.raises(ValueError):
        await provider.save("/etc/passwd", b"x")


async def test_traversal_key_is_rejected(tmp_path):
    provider = LocalStorageProvider(str(tmp_path))

    with pytest.raises(ValueError):
        await provider.save("../escape.bin", b"x")


async def test_symlink_escaping_storage_dir_is_rejected(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "storage"
    root.mkdir()
    (root / "link").symlink_to(outside, target_is_directory=True)
    provider = LocalStorageProvider(str(root))

    with pytest.raises(ValueError):
        await provider.save("link/escape.bin", b"x")
