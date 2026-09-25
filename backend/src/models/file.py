from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class File(Base):
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    ticket_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("tickets.id"))
    message_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("messages.id"))
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    mime: Mapped[str] = mapped_column(Text, nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    original_name: Mapped[str | None] = mapped_column(Text)
    max_token: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
