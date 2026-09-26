from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exceptions import AppException, NotFoundException
from src.services.file_service import MAX_FILE_SIZE, FileService


@pytest.fixture
def storage() -> MagicMock:
    storage = MagicMock()
    storage.save = AsyncMock()
    storage.read = AsyncMock()
    storage.delete = AsyncMock()
    return storage


@pytest.fixture
def files_repo() -> MagicMock:
    repo = MagicMock()
    repo.create = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.list_by_ids = AsyncMock()
    return repo


def _service(db: MagicMock, storage: MagicMock, repo: MagicMock) -> FileService:
    with patch("src.services.file_service.FileRepository", return_value=repo):
        return FileService(db, storage)


async def test_save_rejects_empty_data(storage: MagicMock, files_repo: MagicMock):
    db = AsyncMock()
    service = _service(db, storage, files_repo)

    with pytest.raises(AppException) as exc_info:
        await service.save(b"", "image/png")

    assert exc_info.value.status_code == 400
    storage.save.assert_not_awaited()
    files_repo.create.assert_not_awaited()


async def test_save_rejects_too_large_data(storage: MagicMock, files_repo: MagicMock):
    db = AsyncMock()
    service = _service(db, storage, files_repo)

    with pytest.raises(AppException) as exc_info:
        await service.save(b"x" * (MAX_FILE_SIZE + 1), "image/png")

    assert exc_info.value.status_code == 413
    storage.save.assert_not_awaited()


async def test_save_writes_file_and_creates_row(storage: MagicMock, files_repo: MagicMock):
    db = AsyncMock()
    expected = MagicMock()
    files_repo.create.return_value = expected
    service = _service(db, storage, files_repo)

    result = await service.save(b"data", "image/png", original_name="a.png", ticket_id=7)

    assert result is expected
    key = storage.save.await_args.args[0]
    assert key.startswith("files/")
    assert key.endswith(".png")
    assert storage.save.await_args.args[1] == b"data"
    files_repo.create.assert_awaited_once_with(
        storage_key=key,
        mime="image/png",
        size=4,
        original_name="a.png",
        ticket_id=7,
        message_id=None,
    )
    db.commit.assert_awaited_once()


async def test_save_deletes_file_when_insert_fails(storage: MagicMock, files_repo: MagicMock):
    db = AsyncMock()
    files_repo.create.side_effect = RuntimeError("db down")
    service = _service(db, storage, files_repo)

    with pytest.raises(RuntimeError):
        await service.save(b"data", "image/png")

    key = storage.save.await_args.args[0]
    storage.delete.assert_awaited_once_with(key)
    db.commit.assert_not_awaited()


async def test_get_unattached_returns_files(storage: MagicMock, files_repo: MagicMock):
    db = AsyncMock()
    first = MagicMock()
    first.id = 1
    first.ticket_id = None
    first.message_id = None
    second = MagicMock()
    second.id = 2
    second.ticket_id = None
    second.message_id = None
    files_repo.list_by_ids.return_value = [first, second]
    service = _service(db, storage, files_repo)

    result = await service.get_unattached([1, 2])

    assert result == [first, second]
    files_repo.list_by_ids.assert_awaited_once_with([1, 2])


async def test_get_unattached_rejects_duplicates(storage: MagicMock, files_repo: MagicMock):
    db = AsyncMock()
    service = _service(db, storage, files_repo)

    with pytest.raises(AppException) as exc_info:
        await service.get_unattached([5, 5])

    assert exc_info.value.status_code == 400
    files_repo.list_by_ids.assert_not_awaited()


async def test_get_unattached_rejects_unknown_id(storage: MagicMock, files_repo: MagicMock):
    db = AsyncMock()
    files_repo.list_by_ids.return_value = []
    service = _service(db, storage, files_repo)

    with pytest.raises(AppException) as exc_info:
        await service.get_unattached([9])

    assert exc_info.value.status_code == 400


async def test_get_unattached_rejects_file_attached_to_ticket(
    storage: MagicMock, files_repo: MagicMock
):
    db = AsyncMock()
    attached = MagicMock()
    attached.id = 5
    attached.ticket_id = 99
    attached.message_id = None
    files_repo.list_by_ids.return_value = [attached]
    service = _service(db, storage, files_repo)

    with pytest.raises(AppException) as exc_info:
        await service.get_unattached([5])

    assert exc_info.value.status_code == 400


async def test_get_unattached_rejects_file_attached_to_message(
    storage: MagicMock, files_repo: MagicMock
):
    db = AsyncMock()
    attached = MagicMock()
    attached.id = 5
    attached.ticket_id = None
    attached.message_id = 9
    files_repo.list_by_ids.return_value = [attached]
    service = _service(db, storage, files_repo)

    with pytest.raises(AppException) as exc_info:
        await service.get_unattached([5])

    assert exc_info.value.status_code == 400


async def test_add_writes_blob_and_flushes_without_commit(
    storage: MagicMock, files_repo: MagicMock
):
    db = AsyncMock()
    expected = MagicMock()
    files_repo.create.return_value = expected
    service = _service(db, storage, files_repo)

    result = await service.add(
        b"data", "image/png", original_name="a.png", ticket_id=7, message_id=8
    )

    assert result is expected
    key = storage.save.await_args.args[0]
    files_repo.create.assert_awaited_once_with(
        storage_key=key,
        mime="image/png",
        size=4,
        original_name="a.png",
        ticket_id=7,
        message_id=8,
    )
    db.flush.assert_awaited_once()
    db.commit.assert_not_awaited()
    storage.delete.assert_not_awaited()


async def test_add_rejects_empty_data(storage: MagicMock, files_repo: MagicMock):
    db = AsyncMock()
    service = _service(db, storage, files_repo)

    with pytest.raises(AppException) as exc_info:
        await service.add(b"", "image/png")

    assert exc_info.value.status_code == 400
    storage.save.assert_not_awaited()


async def test_add_deletes_blob_when_flush_fails(storage: MagicMock, files_repo: MagicMock):
    db = AsyncMock()
    files_repo.create.side_effect = RuntimeError("db down")
    service = _service(db, storage, files_repo)

    with pytest.raises(RuntimeError):
        await service.add(b"data", "image/png")

    key = storage.save.await_args.args[0]
    storage.delete.assert_awaited_once_with(key)
    db.flush.assert_not_awaited()
    db.commit.assert_not_awaited()


async def test_save_deletes_file_when_commit_fails(storage: MagicMock, files_repo: MagicMock):
    async def _create(**kwargs):
        file = MagicMock()
        file.storage_key = kwargs["storage_key"]
        return file

    db = AsyncMock()
    db.commit.side_effect = RuntimeError("commit down")
    files_repo.create.side_effect = _create
    service = _service(db, storage, files_repo)

    with pytest.raises(RuntimeError):
        await service.save(b"data", "image/png")

    key = storage.save.await_args.args[0]
    storage.delete.assert_awaited_once_with(key)


async def test_read_returns_file_and_bytes(storage: MagicMock, files_repo: MagicMock):
    db = AsyncMock()
    file = MagicMock()
    file.storage_key = "files/x.bin"
    files_repo.get_by_id.return_value = file
    storage.read.return_value = b"data"
    service = _service(db, storage, files_repo)

    result_file, data = await service.read(5)

    assert result_file is file
    assert data == b"data"
    storage.read.assert_awaited_once_with("files/x.bin")


async def test_read_missing_row_raises_not_found(storage: MagicMock, files_repo: MagicMock):
    db = AsyncMock()
    files_repo.get_by_id.return_value = None
    service = _service(db, storage, files_repo)

    with pytest.raises(NotFoundException):
        await service.read(5)


async def test_read_missing_stored_file_raises_not_found(storage: MagicMock, files_repo: MagicMock):
    db = AsyncMock()
    file = MagicMock()
    file.storage_key = "files/x.bin"
    files_repo.get_by_id.return_value = file
    storage.read.side_effect = FileNotFoundError
    service = _service(db, storage, files_repo)

    with pytest.raises(NotFoundException):
        await service.read(5)
