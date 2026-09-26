from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import SenderType
from src.models.message import Message


class MessageRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        ticket_id: int,
        sender_type: SenderType,
        *,
        author_id: int | None = None,
        text: str | None = None,
        max_message_id: str | None = None,
        created_at: datetime | None = None,
    ) -> Message:
        message = Message(
            ticket_id=ticket_id,
            sender_type=sender_type,
            author_id=author_id,
            text=text,
            max_message_id=max_message_id,
        )
        if created_at is not None:
            message.created_at = created_at
        self.db.add(message)
        await self.db.flush()
        return message

    async def list_by_ticket(self, ticket_id: int) -> list[Message]:
        result = await self.db.execute(
            select(Message)
            .where(Message.ticket_id == ticket_id)
            .order_by(Message.created_at, Message.id)
        )
        return list(result.scalars().all())

    async def get_by_id(
        self, message_id: int, *, populate_existing: bool = False
    ) -> Message | None:
        result = await self.db.execute(
            select(Message)
            .where(Message.id == message_id)
            .execution_options(populate_existing=populate_existing)
        )
        return result.scalar_one_or_none()

    async def get_by_max_message_id(self, max_message_id: str) -> Message | None:
        result = await self.db.execute(
            select(Message).where(Message.max_message_id == max_message_id)
        )
        return result.scalar_one_or_none()
