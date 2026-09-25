from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Identity, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.constants import TicketStatus
from src.db.base import Base


class StatusChange(Base):
    __tablename__ = "status_changes"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    ticket_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tickets.id"), nullable=False)
    from_status: Mapped[TicketStatus | None] = mapped_column(
        Enum(TicketStatus, name="ticket_status")
    )
    to_status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, name="ticket_status"), nullable=False
    )
    changed_by_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
