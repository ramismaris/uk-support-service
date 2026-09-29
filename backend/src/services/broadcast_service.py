import asyncio
import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.background import run_in_background
from src.core.config import settings
from src.core.constants import BroadcastStatus
from src.core.exceptions import AppException, ConflictException, MessengerException
from src.core.texts import (
    BROADCAST_IN_PROGRESS,
    BROADCAST_NO_RECIPIENTS,
    BROADCAST_PHOTO_UNAVAILABLE,
    BUILDING_NOT_FOUND,
)
from src.db.session import AsyncSessionLocal
from src.models.broadcast import Broadcast
from src.models.building import Building
from src.models.user import User
from src.providers.factory import get_messenger_provider, get_storage_provider
from src.providers.messenger_provider import MessengerProvider, OutgoingFile
from src.providers.storage_provider import StorageProvider
from src.repositories.broadcast_repository import BroadcastRepository
from src.repositories.building_repository import BuildingRepository
from src.repositories.file_repository import FileRepository
from src.repositories.user_repository import UserRepository
from src.services.content_service import ContentService
from src.services.file_service import FileService
from src.services.notification_service import MAIN_MENU_ROW

logger = logging.getLogger(__name__)

PROGRESS_SAVE_EVERY = 10


class BroadcastService:
    def __init__(self, db: AsyncSession, messenger: MessengerProvider, storage: StorageProvider):
        self.db = db
        self.messenger = messenger
        self.storage = storage
        self.broadcasts = BroadcastRepository(db)
        self.buildings = BuildingRepository(db)
        self.users = UserRepository(db)
        self.files = FileRepository(db)
        self.file_service = FileService(db, storage)
        self.content = ContentService(db)

    async def count_audience(self, building_ids: list[int] | None) -> int:
        unique_ids = _dedupe(building_ids)
        await self._resolve_buildings(unique_ids)
        recipients = await self.users.list_broadcast_recipients(unique_ids)
        return len(recipients)

    async def create(
        self,
        admin: User,
        text: str,
        file_id: int | None,
        building_ids: list[int] | None,
    ) -> Broadcast:
        unique_ids = _dedupe(building_ids)
        buildings = await self._resolve_buildings(unique_ids)

        photo = None
        if file_id is not None:
            photo = await self.content.ensure_content_image(file_id)

        recipients = await self.users.list_broadcast_recipients(unique_ids)
        if not recipients:
            raise AppException(BROADCAST_NO_RECIPIENTS, status_code=400)

        if photo is not None:
            # Cache the Max token before the row exists: a failed upload leaves no broadcast.
            try:
                await self.file_service.get_max_token(photo, self.messenger)
            except OSError:
                raise AppException(BROADCAST_PHOTO_UNAVAILABLE, status_code=400)

        try:
            broadcast = await self.broadcasts.create(
                author_id=admin.id,
                text=text,
                file_id=file_id,
                recipients_total=len(recipients),
                buildings=buildings,
            )
        except IntegrityError:
            await self.db.rollback()
            raise ConflictException(BROADCAST_IN_PROGRESS)

        broadcast.author = admin
        await self.db.commit()

        run_in_background(run_broadcast(broadcast.id, recipients), name=f"broadcast-{broadcast.id}")
        return broadcast

    async def send(self, broadcast_id: int, max_user_ids: list[int]) -> None:
        broadcast = await self.broadcasts.get_by_id(broadcast_id)
        if broadcast is None:
            logger.warning("Broadcast %s not found", broadcast_id)
            return

        files = await self._outgoing_files(broadcast)
        delivered = 0
        failed = 0
        try:
            for index, max_user_id in enumerate(max_user_ids):
                try:
                    await self.messenger.send_message(
                        max_user_id,
                        broadcast.text,
                        buttons=[MAIN_MENU_ROW],
                        files=files,
                        markdown=True,
                    )
                    delivered += 1
                except MessengerException:
                    failed += 1
                    logger.warning("Broadcast %s: a message was not delivered", broadcast_id)

                if index < len(max_user_ids) - 1:
                    await asyncio.sleep(1 / settings.broadcast_rate_per_second)

                if (index + 1) % PROGRESS_SAVE_EVERY == 0:
                    await self.broadcasts.save_progress(
                        broadcast_id, delivered_count=delivered, failed_count=failed
                    )
                    await self.db.commit()

            await self.broadcasts.save_progress(
                broadcast_id, delivered_count=delivered, failed_count=failed
            )
            await self.broadcasts.finish(broadcast_id, BroadcastStatus.DONE)
            await self.db.commit()
        except Exception:
            logger.exception("Broadcast %s interrupted", broadcast_id)
            await self.db.rollback()
            await self.broadcasts.save_progress(
                broadcast_id, delivered_count=delivered, failed_count=failed
            )
            await self.broadcasts.finish(broadcast_id, BroadcastStatus.INTERRUPTED)
            await self.db.commit()

    async def list_for_admin(self, skip: int, limit: int) -> tuple[list[Broadcast], int]:
        items = await self.broadcasts.list(skip=skip, limit=limit)
        total = await self.broadcasts.count()
        return items, total

    async def _outgoing_files(self, broadcast: Broadcast) -> list[OutgoingFile] | None:
        if broadcast.file_id is None:
            return None
        file = await self.files.get_by_id(broadcast.file_id)
        if file is None or file.max_token is None:
            return None
        return [OutgoingFile(file.max_token, file.mime)]

    async def _resolve_buildings(self, building_ids: list[int] | None) -> list[Building]:
        if building_ids is None:
            return []
        buildings = await self.buildings.list_by_ids(building_ids)
        if len(buildings) != len(building_ids) or any(
            not building.is_active for building in buildings
        ):
            raise AppException(BUILDING_NOT_FOUND, status_code=400)
        return buildings


def _dedupe(building_ids: list[int] | None) -> list[int] | None:
    if building_ids is None:
        return None
    return list(dict.fromkeys(building_ids))


async def run_broadcast(broadcast_id: int, max_user_ids: list[int]) -> None:
    async with AsyncSessionLocal() as db:
        service = BroadcastService(db, get_messenger_provider(), get_storage_provider())
        await service.send(broadcast_id, max_user_ids)


async def interrupt_stale_broadcasts() -> None:
    async with AsyncSessionLocal() as db:
        count = await BroadcastRepository(db).interrupt_sending()
        await db.commit()
    if count:
        logger.warning("Interrupted %s stale broadcasts", count)
