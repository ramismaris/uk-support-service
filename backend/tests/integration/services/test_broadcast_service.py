from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.config import settings
from src.core.constants import BroadcastStatus, UserRole
from src.core.exceptions import MessengerException
from src.repositories.broadcast_repository import BroadcastRepository
from src.repositories.user_repository import UserRepository
from src.services.broadcast_service import BroadcastService, interrupt_stale_broadcasts


async def _author(db: AsyncSession):
    return await UserRepository(db).create(max_user_id=1, first_name="Анна", role=UserRole.ADMIN)


async def test_send_persists_counters_and_done(db: AsyncSession, monkeypatch) -> None:
    monkeypatch.setattr(settings, "broadcast_rate_per_second", 1000)
    repository = BroadcastRepository(db)
    author = await _author(db)
    broadcast = await repository.create(
        author_id=author.id,
        text="Уважаемые жильцы",
        file_id=None,
        recipients_total=3,
        buildings=[],
    )
    await db.commit()

    messenger = AsyncMock()
    messenger.send_message.side_effect = [None, MessengerException(), None]

    await BroadcastService(db, messenger, MagicMock()).send(broadcast.id, [11, 12, 13])

    assert messenger.send_message.await_count == 3
    broadcast_id = broadcast.id
    db.expire_all()
    reloaded = await repository.get_by_id(broadcast_id)
    assert reloaded is not None
    assert reloaded.status == BroadcastStatus.DONE
    assert reloaded.delivered_count == 2
    assert reloaded.failed_count == 1
    assert reloaded.finished_at is not None


async def test_interrupt_stale_broadcasts_marks_only_sending(
    db: AsyncSession, session_factory: async_sessionmaker[AsyncSession]
) -> None:
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

    with patch("src.services.broadcast_service.AsyncSessionLocal", session_factory):
        await interrupt_stale_broadcasts()

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
