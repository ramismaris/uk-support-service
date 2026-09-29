import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import BroadcastStatus, UserRole
from src.repositories.broadcast_repository import BroadcastRepository
from src.repositories.building_repository import BuildingRepository
from src.repositories.user_repository import UserRepository


async def _author(db: AsyncSession):
    return await UserRepository(db).create(max_user_id=1, first_name="Анна", role=UserRole.ADMIN)


async def test_second_sending_violates_unique_index(db: AsyncSession) -> None:
    repository = BroadcastRepository(db)
    author = await _author(db)
    await repository.create(
        author_id=author.id, text="Первая", file_id=None, recipients_total=1, buildings=[]
    )
    await db.commit()

    with pytest.raises(IntegrityError):
        await repository.create(
            author_id=author.id, text="Вторая", file_id=None, recipients_total=1, buildings=[]
        )
    await db.rollback()


async def test_done_and_interrupted_do_not_block_sending(db: AsyncSession) -> None:
    repository = BroadcastRepository(db)
    author = await _author(db)
    sending = await repository.create(
        author_id=author.id, text="Идёт", file_id=None, recipients_total=1, buildings=[]
    )
    await db.commit()

    done = await repository.create(
        author_id=author.id,
        text="Готово",
        file_id=None,
        recipients_total=1,
        buildings=[],
        status=BroadcastStatus.DONE,
    )
    interrupted = await repository.create(
        author_id=author.id,
        text="Прервано",
        file_id=None,
        recipients_total=1,
        buildings=[],
        status=BroadcastStatus.INTERRUPTED,
    )
    await db.commit()

    assert {done.status, interrupted.status} == {
        BroadcastStatus.DONE,
        BroadcastStatus.INTERRUPTED,
    }

    sending.status = BroadcastStatus.DONE
    await db.commit()
    second = await repository.create(
        author_id=author.id, text="Новая", file_id=None, recipients_total=1, buildings=[]
    )
    await db.commit()

    assert second.id != sending.id


async def test_interrupt_sending_changes_only_sending(db: AsyncSession) -> None:
    repository = BroadcastRepository(db)
    author = await _author(db)
    sending = await repository.create(
        author_id=author.id, text="Идёт", file_id=None, recipients_total=1, buildings=[]
    )
    done = await repository.create(
        author_id=author.id,
        text="Готово",
        file_id=None,
        recipients_total=1,
        buildings=[],
        status=BroadcastStatus.DONE,
    )
    await db.commit()

    count = await repository.interrupt_sending()
    await db.commit()

    assert count == 1
    sending_id = sending.id
    done_id = done.id
    db.expire_all()
    reloaded = await repository.get_by_id(sending_id)
    assert reloaded is not None
    assert reloaded.status == BroadcastStatus.INTERRUPTED
    assert reloaded.finished_at is not None
    still_done = await repository.get_by_id(done_id)
    assert still_done is not None
    assert still_done.status == BroadcastStatus.DONE
    assert still_done.finished_at is None


async def test_interrupt_sending_without_sending_is_a_noop(db: AsyncSession) -> None:
    repository = BroadcastRepository(db)
    author = await _author(db)
    done = await repository.create(
        author_id=author.id,
        text="Готово",
        file_id=None,
        recipients_total=1,
        buildings=[],
        status=BroadcastStatus.DONE,
    )
    await db.commit()

    assert await repository.interrupt_sending() == 0

    done_id = done.id
    db.expire_all()
    reloaded = await repository.get_by_id(done_id)
    assert reloaded is not None
    assert reloaded.status == BroadcastStatus.DONE


async def test_list_is_newest_first_with_author_and_buildings(db: AsyncSession) -> None:
    repository = BroadcastRepository(db)
    author = await _author(db)
    building = await BuildingRepository(db).create("ул. Ленина, 1")
    first = await repository.create(
        author_id=author.id,
        text="Первая",
        file_id=None,
        recipients_total=1,
        buildings=[building],
        status=BroadcastStatus.DONE,
    )
    await db.commit()
    second = await repository.create(
        author_id=author.id,
        text="Вторая",
        file_id=None,
        recipients_total=0,
        buildings=[],
        status=BroadcastStatus.DONE,
    )
    await db.commit()
    db.expire_all()

    items = await repository.list(skip=0, limit=10)

    assert [broadcast.id for broadcast in items] == [second.id, first.id]
    assert items[1].author.id == author.id
    assert [b.address for b in items[1].buildings] == ["ул. Ленина, 1"]
    assert items[0].buildings == []


async def test_list_pages_and_count_is_total(db: AsyncSession) -> None:
    repository = BroadcastRepository(db)
    author = await _author(db)
    for index in range(3):
        await repository.create(
            author_id=author.id,
            text=f"Рассылка {index}",
            file_id=None,
            recipients_total=1,
            buildings=[],
            status=BroadcastStatus.DONE,
        )
    await db.commit()

    assert await repository.count() == 3
    assert len(await repository.list(skip=1, limit=1)) == 1


async def test_save_progress_updates_counters(db: AsyncSession) -> None:
    repository = BroadcastRepository(db)
    author = await _author(db)
    broadcast = await repository.create(
        author_id=author.id, text="Идёт", file_id=None, recipients_total=5, buildings=[]
    )
    await db.commit()

    await repository.save_progress(broadcast.id, delivered_count=2, failed_count=1)
    await db.commit()
    broadcast_id = broadcast.id
    db.expire_all()

    reloaded = await repository.get_by_id(broadcast_id)
    assert reloaded is not None
    assert reloaded.delivered_count == 2
    assert reloaded.failed_count == 1
    assert reloaded.status == BroadcastStatus.SENDING


async def test_finish_sets_status_and_finished_at(db: AsyncSession) -> None:
    repository = BroadcastRepository(db)
    author = await _author(db)
    broadcast = await repository.create(
        author_id=author.id, text="Идёт", file_id=None, recipients_total=1, buildings=[]
    )
    await db.commit()

    await repository.finish(broadcast.id, BroadcastStatus.DONE)
    await db.commit()
    broadcast_id = broadcast.id
    db.expire_all()

    reloaded = await repository.get_by_id(broadcast_id)
    assert reloaded is not None
    assert reloaded.status == BroadcastStatus.DONE
    assert reloaded.finished_at is not None
