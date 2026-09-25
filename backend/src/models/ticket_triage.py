from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from src.core.constants import TicketPriority
from src.db.base import Base


class TicketTriage(Base):
    __tablename__ = "ticket_triage"

    ticket_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tickets.id"), primary_key=True)
    suggested_category_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("categories.id")
    )
    urgency: Mapped[TicketPriority] = mapped_column(
        Enum(TicketPriority, name="ticket_priority"), nullable=False
    )
    is_relevant: Mapped[bool] = mapped_column(Boolean, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    raw: Mapped[dict | None] = mapped_column(postgresql.JSONB)
    overridden_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
