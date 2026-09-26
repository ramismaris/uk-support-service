import logging
import re

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.background import run_in_background
from src.core.constants import TicketStatus, TicketType
from src.core.exceptions import (
    AppException,
    ConflictException,
    MessengerException,
    NotFoundException,
)
from src.core.texts import (
    APARTMENT_INVALID,
    BUILDING_NOT_FOUND,
    CATEGORY_NOT_FOUND,
    DESCRIPTION_LIMIT,
    DESCRIPTION_REQUIRED,
    DESCRIPTION_TOO_LONG,
    PHONE_INVALID,
    PHOTO_NOT_IMAGE,
    RESIDENCE_NOT_FOUND,
    TICKET_CLOSED_FOR_CLIENT,
    TICKET_NOT_FOUND,
)
from src.models.building import Building
from src.models.category import Category
from src.models.file import File
from src.models.residence import Residence
from src.models.ticket import Ticket
from src.models.user import User
from src.providers.messenger_provider import MessengerProvider
from src.providers.storage_provider import StorageProvider
from src.repositories.building_repository import BuildingRepository
from src.repositories.category_repository import CategoryRepository
from src.repositories.residence_repository import ResidenceRepository
from src.repositories.status_change_repository import StatusChangeRepository
from src.repositories.ticket_repository import TicketRepository
from src.services import ticket_rules
from src.services.file_service import MAX_FILE_SIZE, FileService
from src.services.notification_service import NotificationService, notify_staff_about_new_ticket

logger = logging.getLogger(__name__)

_APARTMENT_PATTERN = re.compile(r"[0-9A-Za-zА-Яа-яЁё][0-9A-Za-zА-Яа-яЁё /.-]{0,19}")


def validate_apartment(value: str) -> str:
    apartment = value.strip()
    if _APARTMENT_PATTERN.fullmatch(apartment) is None:
        raise AppException(APARTMENT_INVALID, status_code=400)
    return apartment


def validate_description(value: str) -> str:
    description = value.strip()
    if not description:
        raise AppException(DESCRIPTION_REQUIRED, status_code=400)
    if len(description) > DESCRIPTION_LIMIT:
        raise AppException(DESCRIPTION_TOO_LONG, status_code=400)
    return description


class ClientTicketService:
    def __init__(self, db: AsyncSession, messenger: MessengerProvider, storage: StorageProvider):
        self.db = db
        self.messenger = messenger
        self.storage = storage
        self.tickets = TicketRepository(db)
        self.file_service = FileService(db, storage)
        self.status_changes = StatusChangeRepository(db)
        self.categories = CategoryRepository(db)
        self.buildings = BuildingRepository(db)
        self.residences = ResidenceRepository(db)
        self.notifications = NotificationService(db, messenger)

    async def set_phone(self, client: User, raw: str) -> None:
        digits = re.sub(r"\D", "", raw)
        if len(digits) == 11 and digits.startswith("8"):
            digits = "7" + digits[1:]
        if not 10 <= len(digits) <= 15:
            raise AppException(PHONE_INVALID, status_code=400)
        client.phone = f"+{digits}"
        await self.db.commit()

    async def list_categories(self) -> list[Category]:
        return await self.categories.list_active()

    async def list_buildings(self) -> list[Building]:
        return await self.buildings.list_active()

    async def list_residences(self, client: User) -> list[Residence]:
        return await self.residences.list_by_user(client.id)

    async def add_residence(self, client: User, building_id: int, apartment: str) -> Residence:
        building = await self.buildings.get_by_id(building_id)
        if building is None or not building.is_active:
            raise NotFoundException(BUILDING_NOT_FOUND)

        apartment = validate_apartment(apartment)

        existing = await self.residences.get(client.id, building_id, apartment)
        if existing is not None:
            return existing

        is_primary = not await self.residences.list_by_user(client.id)
        residence = await self.residences.create(
            client.id, building.id, apartment, is_primary=is_primary
        )
        await self.db.commit()
        return residence

    async def get_residence(self, client: User, residence_id: int) -> Residence:
        residence = await self.residences.get_by_id(residence_id)
        if residence is None or residence.user_id != client.id:
            raise NotFoundException(RESIDENCE_NOT_FOUND)
        return residence

    async def save_photo(self, url: str) -> File:
        data, mime = await self.messenger.download_file(url, MAX_FILE_SIZE)
        if not mime.startswith("image/"):
            raise AppException(PHOTO_NOT_IMAGE, status_code=400)
        return await self.file_service.save(data, mime)

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
        description = validate_description(description)
        apartment = validate_apartment(apartment)
        if preferred_time is not None:
            preferred_time = preferred_time.strip() or None

        category = await self.categories.get_by_id(category_id)
        if category is None or not category.is_active:
            raise NotFoundException(CATEGORY_NOT_FOUND)

        building = await self.buildings.get_by_id(building_id)
        if building is None or not building.is_active:
            raise NotFoundException(BUILDING_NOT_FOUND)

        return await self._create_ticket(
            client,
            ticket_type=TicketType.REQUEST,
            description=description,
            category=category,
            building=building,
            apartment=apartment,
            preferred_time=preferred_time,
            photo_ids=photo_ids,
        )

    async def create_question(
        self,
        client: User,
        *,
        description: str,
        photo_ids: list[int],
    ) -> Ticket:
        description = validate_description(description)

        return await self._create_ticket(
            client,
            ticket_type=TicketType.QUESTION,
            description=description,
            category=None,
            building=None,
            apartment=None,
            preferred_time=None,
            photo_ids=photo_ids,
        )

    async def set_active_ticket(self, client: User, ticket_id: int) -> Ticket:
        ticket = await self.tickets.get_by_id(ticket_id)
        if ticket is None or ticket.client_id != client.id:
            raise NotFoundException(TICKET_NOT_FOUND)
        if not ticket_rules.is_open(ticket.status):
            raise ConflictException(TICKET_CLOSED_FOR_CLIENT.format(ticket_id=ticket.id))

        client.active_ticket_id = ticket.id
        await self.db.commit()
        return ticket

    async def list_open_tickets(self, client: User) -> list[Ticket]:
        return await self.tickets.list_by_client(client.id, statuses=ticket_rules.OPEN_STATUSES)

    async def get_ticket(self, client: User, ticket_id: int) -> Ticket:
        ticket = await self.tickets.get_by_id(ticket_id)
        if ticket is None or ticket.client_id != client.id:
            raise NotFoundException(TICKET_NOT_FOUND)
        return ticket

    async def _create_ticket(
        self,
        client: User,
        *,
        ticket_type: TicketType,
        description: str,
        category: Category | None,
        building: Building | None,
        apartment: str | None,
        preferred_time: str | None,
        photo_ids: list[int],
    ) -> Ticket:
        files = await self.file_service.get_unattached(photo_ids)

        ticket = await self.tickets.create(
            type=ticket_type,
            status=TicketStatus.NEW,
            client_id=client.id,
            description=description,
            category_id=category.id if category is not None else None,
            building_id=building.id if building is not None else None,
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
