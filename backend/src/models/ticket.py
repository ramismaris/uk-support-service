from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Identity,
    SmallInteger,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.constants import TicketPriority, TicketStatus, TicketType
from src.db.base import Base
from src.models.building import Building
from src.models.category import Category
from src.models.user import User


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="rating_range"),
        CheckConstraint(
            "type = 'QUESTION' OR (building_id IS NOT NULL AND apartment IS NOT NULL "
            "AND category_id IS NOT NULL)",
            name="request_has_address",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True, start=1000), primary_key=True)
    type: Mapped[TicketType] = mapped_column(Enum(TicketType, name="ticket_type"), nullable=False)
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, name="ticket_status"), nullable=False, index=True
    )
    priority: Mapped[TicketPriority] = mapped_column(
        Enum(TicketPriority, name="ticket_priority"),
        nullable=False,
        server_default=TicketPriority.NORMAL.value,
    )
    client_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False, index=True
    )
    assignee_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    category_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("categories.id"))
    building_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("buildings.id"), index=True
    )
    apartment: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    contact_phone: Mapped[str | None] = mapped_column(Text)
    preferred_time: Mapped[str | None] = mapped_column(Text)
    status_message_max_id: Mapped[str | None] = mapped_column(Text)
    last_client_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    staff_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rating: Mapped[int | None] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    client: Mapped[User] = relationship(foreign_keys=[client_id], lazy="selectin")
    assignee: Mapped[User | None] = relationship(foreign_keys=[assignee_id], lazy="selectin")
    category: Mapped[Category | None] = relationship(lazy="selectin")
    building: Mapped[Building | None] = relationship(lazy="selectin")
