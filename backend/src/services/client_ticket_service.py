import logging
import re

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.background import run_in_background
from src.core.constants import TicketStatus, TicketType
from src.core.exceptions import AppException, MessengerException, NotFoundException
from src.core.texts import (
    APARTMENT_INVALID,
    BUILDING_NOT_FOUND,
    CATEGORY_NOT_FOUND,
    DESCRIPTION_REQUIRED,
    PHOTO_ALREADY_ATTACHED,
    PHOTO_NOT_FOUND,
    PHOTO_NOT_IMAGE,
    PHOTOS_DUPLICATED,
)
from src.models.file import File
from src.models.ticket import Ticket
from src.models.user import User
from src.providers.messenger_provider import MessengerProvider
from src.providers.storage_provider import StorageProvider
from src.repositories.building_repository import BuildingRepository
from src.repositories.category_repository import CategoryRepository
from src.repositories.file_repository import FileRepository
from src.repositories.status_change_repository import StatusChangeRepository
from src.repositories.ticket_repository import TicketRepository
from src.services.file_service import MAX_FILE_SIZE, FileService
from src.services.notification_service import NotificationService, notify_staff_about_new_ticket

logger = logging.getLogger(__name__)

_APARTMENT_PATTERN = re.compile(r"[0-9A-Za-zА-Яа-яЁё][0-9A-Za-zА-Яа-яЁё /.-]{0,19}")


def validate_apartment(value: str) -> str:
    apartment = value.strip()
    if _APARTMENT_PATTERN.fullmatch(apartment) is None:
        raise AppException(APARTMENT_INVALID, status_code=400)
    return apartment


class ClientTicketService:
    def __init__(self, db: AsyncSession, messenger: MessengerProvider, storage: StorageProvider):
        self.db = db
        self.messenger = messenger
        self.storage = storage
        self.tickets = TicketRepository(db)
        self.files = FileRepository(db)
        self.status_changes = StatusChangeRepository(db)
        self.categories = CategoryRepository(db)
        self.buildings = BuildingRepository(db)
        self.notifications = NotificationService(db, messenger)

    async def save_photo(self, url: str) -> File:
        data, mime = await self.messenger.download_file(url, MAX_FILE_SIZE)
        if not mime.startswith("image/"):
            raise AppException(PHOTO_NOT_IMAGE, status_code=400)
        return await FileService(self.db, self.storage).save(data, mime)

    async def create_request(
        self,
        client: User,
        *,
        category_id: int,
        building_id: int,
        apartment: str,
        description: str,
        preferred_time: str | None,
        photo_ids: list[int],
    ) -> Ticket:
        description = description.strip()
        if not description:
            raise AppException(DESCRIPTION_REQUIRED, status_code=400)
        apartment = validate_apartment(apartment)
        if preferred_time is not None:
            preferred_time = preferred_time.strip() or None

        category = await self.categories.get_by_id(category_id)
        if category is None or not category.is_active:
            raise NotFoundException(CATEGORY_NOT_FOUND)

        building = await self.buildings.get_by_id(building_id)
        if building is None or not building.is_active:
            raise NotFoundException(BUILDING_NOT_FOUND)

        if len(set(photo_ids)) != len(photo_ids):
            raise AppException(PHOTOS_DUPLICATED, status_code=400)

        files = await self.files.list_by_ids(photo_ids)
        files_by_id = {file.id: file for file in files}
        for photo_id in photo_ids:
            file = files_by_id.get(photo_id)
            if file is None:
                raise AppException(PHOTO_NOT_FOUND, status_code=400)
            if file.ticket_id is not None or file.message_id is not None:
                raise AppException(PHOTO_ALREADY_ATTACHED, status_code=400)

        ticket = await self.tickets.create(
            type=TicketType.REQUEST,
            status=TicketStatus.NEW,
            client_id=client.id,
            description=description,
            category_id=category.id,
            building_id=building.id,
            apartment=apartment,
            contact_phone=client.phone,
            preferred_time=preferred_time,
        )
        ticket.client = client
        ticket.category = category
        ticket.building = building

        await self.status_changes.create(
            ticket.id,
            None,
            TicketStatus.NEW,
            changed_by_id=client.id,
        )

        for file in files:
            file.ticket_id = ticket.id

        client.active_ticket_id = ticket.id
        await self.db.commit()

        try:
            await self.notifications.send_status_card(ticket)
        except MessengerException:
            logger.warning("Failed to send status card for ticket %s", ticket.id)

        run_in_background(
            notify_staff_about_new_ticket(ticket.id), name=f"notify-staff-{ticket.id}"
        )
        return ticket
