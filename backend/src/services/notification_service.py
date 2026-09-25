import logging
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.constants import ButtonType
from src.core.exceptions import MessengerException
from src.core.texts import STAFF_NEW_TICKET_BUTTON, new_ticket_staff_text
from src.db.session import AsyncSessionLocal
from src.models.ticket import Ticket
from src.providers.factory import get_messenger_provider
from src.providers.messenger_provider import Button, MessengerProvider
from src.repositories.file_repository import FileRepository
from src.repositories.status_change_repository import StatusChangeRepository
from src.repositories.ticket_repository import TicketRepository
from src.repositories.user_repository import UserRepository
from src.services.status_card import build_status_card

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, db: AsyncSession, messenger: MessengerProvider):
        self.db = db
        self.messenger = messenger
        self.tickets = TicketRepository(db)
        self.files = FileRepository(db)
        self.status_changes = StatusChangeRepository(db)
        self.users = UserRepository(db)

    async def send_status_card(self, ticket: Ticket) -> None:
        history = await self.status_changes.list_by_ticket(ticket.id)
        text = build_status_card(ticket, history, ZoneInfo(settings.timezone))
        message_id = await self.messenger.send_message(
            ticket.client.max_user_id, text, markdown=True
        )
        if message_id is not None:
            ticket.status_message_max_id = message_id
            await self.db.commit()

    async def notify_staff_new_ticket(self, ticket_id: int) -> None:
        ticket = await self.tickets.get_by_id(ticket_id)
        photos_count = len(await self.files.list_by_ticket(ticket_id))
        text = new_ticket_staff_text(
            ticket_id=ticket.id,
            ticket_type=ticket.type,
            category_title=ticket.category.title if ticket.category else None,
            building_address=ticket.building.address if ticket.building else None,
            apartment=ticket.apartment,
            client_first_name=ticket.client.first_name,
            client_last_name=ticket.client.last_name,
            client_phone=ticket.contact_phone,
            photos_count=photos_count,
            description=ticket.description,
        )
        buttons = [[Button(STAFF_NEW_TICKET_BUTTON, ButtonType.OPEN_APP, f"ticket_{ticket.id}")]]
        for staff in await self.users.list_staff():
            try:
                await self.messenger.send_message(staff.max_user_id, text, buttons=buttons)
            except MessengerException:
                logger.warning("Failed to notify staff user %s", staff.id)


async def notify_staff_about_new_ticket(ticket_id: int) -> None:
    async with AsyncSessionLocal() as db:
        service = NotificationService(db, get_messenger_provider())
        await service.notify_staff_new_ticket(ticket_id)
