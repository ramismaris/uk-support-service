import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.background import run_in_background
from src.core.constants import CHAT_TICKET_PREFIX, ButtonType, SenderType
from src.core.exceptions import (
    AppException,
    ConflictException,
    MessengerException,
    NotFoundException,
)
from src.core.texts import (
    MESSAGE_EMPTY,
    MESSAGE_FILES_MAX,
    MESSAGE_FILES_MIXED,
    MESSAGE_LIMIT,
    MESSAGE_TOO_LONG,
    MESSAGE_TOO_MANY_FILES,
    TICKET_CLOSED_FOR_CLIENT,
    TICKET_CLOSED_FOR_STAFF,
    TICKET_NOT_FOUND,
    TICKET_REPLY_BUTTON,
    staff_message_client_text,
)
from src.models.message import Message
from src.models.user import User
from src.providers.messenger_provider import Button, MessengerProvider, OutgoingFile
from src.providers.storage_provider import StorageProvider
from src.repositories.message_repository import MessageRepository
from src.repositories.status_change_repository import StatusChangeRepository
from src.repositories.ticket_repository import TicketRepository
from src.services import ticket_rules
from src.services.file_service import FileService
from src.services.notification_service import (
    NotificationService,
    notify_staff_about_client_message,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UploadedFile:
    data: bytes
    mime: str
    filename: str | None


class MessageService:
    def __init__(self, db: AsyncSession, messenger: MessengerProvider, storage: StorageProvider):
        self.db = db
        self.messenger = messenger
        self.storage = storage
        self.messages = MessageRepository(db)
        self.tickets = TicketRepository(db)
        self.status_changes = StatusChangeRepository(db)
        self.file_service = FileService(db, storage)
        self.notifications = NotificationService(db, messenger)

    async def send_staff_message(
        self,
        ticket_id: int,
        author: User,
        text: str | None,
        uploads: list[UploadedFile],
    ) -> Message:
        text = text.strip() if text is not None else None
        text = text or None
        uploads = [self._normalize_upload(upload) for upload in uploads]

        if text is None and not uploads:
            raise AppException(MESSAGE_EMPTY, status_code=400)
        if text is not None and len(text) > MESSAGE_LIMIT:
            raise AppException(MESSAGE_TOO_LONG, status_code=400)
        if len(uploads) > MESSAGE_FILES_MAX:
            raise AppException(MESSAGE_TOO_MANY_FILES, status_code=400)
        if len(uploads) > 1 and any(not upload.mime.startswith("image/") for upload in uploads):
            raise AppException(MESSAGE_FILES_MIXED, status_code=400)
        for upload in uploads:
            self.file_service.check_data(upload.data)

        ticket = await self.tickets.get_by_id(ticket_id)
        if ticket is None:
            raise NotFoundException(TICKET_NOT_FOUND)
        if not ticket_rules.is_open(ticket.status):
            raise ConflictException(TICKET_CLOSED_FOR_STAFF)

        tokens = [
            await self.messenger.upload_file(upload.data, upload.mime, upload.filename)
            for upload in uploads
        ]
        files = [
            OutgoingFile(token, upload.mime)
            for token, upload in zip(tokens, uploads, strict=True)
            if token is not None
        ]
        buttons = [
            [Button(TICKET_REPLY_BUTTON, ButtonType.CALLBACK, f"{CHAT_TICKET_PREFIX}{ticket.id}")]
        ]
        max_message_id = await self.messenger.send_message(
            ticket.client.max_user_id,
            staff_message_client_text(ticket_id=ticket.id, ticket_type=ticket.type, text=text),
            buttons=buttons,
            files=files,
            markdown=False,
        )

        ticket = await self.tickets.get_by_id_for_update(ticket_id)
        message = await self.messages.create(
            ticket.id,
            SenderType.STAFF,
            author_id=author.id,
            text=text,
            max_message_id=max_message_id,
        )
        added_keys: list[str] = []
        for token, upload in zip(tokens, uploads, strict=True):
            file = await self.file_service.add(
                upload.data,
                upload.mime,
                upload.filename,
                ticket_id=ticket.id,
                message_id=message.id,
            )
            file.max_token = token
            added_keys.append(file.storage_key)

        new_status = ticket_rules.status_after_staff_message(ticket.status)
        if new_status is not None:
            await self.status_changes.create(
                ticket.id,
                ticket.status,
                new_status,
                changed_by_id=None,
            )
            ticket.status = new_status
            ticket.assignee_id = author.id

        ticket.staff_seen_at = datetime.now(UTC)
        try:
            await self.db.commit()
        except Exception:
            for key in added_keys:
                await self.storage.delete(key)
            raise

        if new_status is not None:
            try:
                await self.notifications.update_status_card(ticket)
            except MessengerException:
                logger.warning("Failed to update status card for ticket %s", ticket.id)

        return await self.messages.get_by_id(message.id)

    async def resolve_client_route(
        self,
        client: User,
        reply_to_max_message_id: str | None,
    ) -> ticket_rules.ToTicket | ticket_rules.AskWhichTicket | ticket_rules.OfferNewQuestion:
        reply_ticket_id = None
        if reply_to_max_message_id is not None:
            message = await self.messages.get_by_max_message_id(reply_to_max_message_id)
            if message is not None:
                reply_ticket_id = message.ticket_id
            else:
                ticket = await self.tickets.get_by_status_message_max_id(reply_to_max_message_id)
                if ticket is not None:
                    reply_ticket_id = ticket.id

        open_tickets = await self.tickets.list_by_client(
            client.id, statuses=ticket_rules.OPEN_STATUSES
        )
        open_ids = [ticket.id for ticket in open_tickets]
        return ticket_rules.route_client_message(
            reply_ticket_id,
            client.active_ticket_id,
            open_ids,
        )

    async def add_client_message(
        self,
        client: User,
        ticket_id: int,
        *,
        text: str | None,
        file_ids: list[int],
        max_message_id: str | None,
    ) -> Message:
        text = text.strip() if text is not None else None
        text = text or None

        if text is None and not file_ids:
            raise AppException(MESSAGE_EMPTY, status_code=400)

        if max_message_id is not None:
            existing = await self.messages.get_by_max_message_id(max_message_id)
            if existing is not None:
                return existing

        ticket = await self.tickets.get_by_id_for_update(ticket_id)
        if ticket is None or ticket.client_id != client.id:
            raise NotFoundException(TICKET_NOT_FOUND)
        if not ticket_rules.is_open(ticket.status):
            raise ConflictException(TICKET_CLOSED_FOR_CLIENT.format(ticket_id=ticket.id))

        files = await self.file_service.get_unattached(file_ids)

        message = await self.messages.create(
            ticket.id,
            SenderType.CLIENT,
            author_id=client.id,
            text=text,
            max_message_id=max_message_id,
        )
        for file in files:
            file.ticket_id = ticket.id
            file.message_id = message.id

        ticket.last_client_message_at = datetime.now(UTC)
        client.active_ticket_id = ticket.id

        new_status = ticket_rules.status_after_client_message(ticket.status)
        if new_status is not None:
            await self.status_changes.create(
                ticket.id,
                ticket.status,
                new_status,
                changed_by_id=None,
            )
            ticket.status = new_status

        await self.db.commit()

        if new_status is not None:
            try:
                await self.notifications.update_status_card(ticket)
            except MessengerException:
                logger.warning("Failed to update status card for ticket %s", ticket.id)

        run_in_background(
            notify_staff_about_client_message(message.id),
            name=f"notify-client-message-{message.id}",
        )
        return message

    @staticmethod
    def _normalize_upload(upload: UploadedFile) -> UploadedFile:
        filename = upload.filename.strip() if upload.filename else None
        return UploadedFile(
            data=upload.data,
            mime=upload.mime.strip().lower() or "application/octet-stream",
            filename=filename or None,
        )
