from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Identity, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.constants import SenderType
from src.db.base import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    ticket_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tickets.id"), nullable=False)
    sender_type: Mapped[SenderType] = mapped_column(
        Enum(SenderType, name="sender_type"), nullable=False
    )
    author_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    text: Mapped[str | None] = mapped_column(Text)
    max_message_id: Mapped[str | None] = mapped_column(Text, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
