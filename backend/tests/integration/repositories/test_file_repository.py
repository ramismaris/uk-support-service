from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.file_repository import FileRepository


async def _make_file(repository: FileRepository, name: str):
    return await repository.create(storage_key=f"files/{name}", mime="image/png", size=1)


async def test_list_by_ids_returns_matching_files(db: AsyncSession) -> None:
    repository = FileRepository(db)
    first = await _make_file(repository, "a.png")
    second = await _make_file(repository, "b.png")
    await _make_file(repository, "c.png")
    await db.commit()

    files = await repository.list_by_ids([first.id, second.id])

    assert [file.id for file in files] == [first.id, second.id]


async def test_list_by_ids_empty_returns_empty(db: AsyncSession) -> None:
    repository = FileRepository(db)
    await _make_file(repository, "a.png")
    await db.commit()

    assert await repository.list_by_ids([]) == []


async def test_list_by_ids_skips_missing_ids(db: AsyncSession) -> None:
    repository = FileRepository(db)
    existing = await _make_file(repository, "a.png")
    await db.commit()

    files = await repository.list_by_ids([existing.id, 999999])

    assert [file.id for file in files] == [existing.id]
