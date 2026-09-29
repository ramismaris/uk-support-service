from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.constants import BroadcastStatus
from src.db.base import Base
from src.models.building import Building
from src.models.user import User


class BroadcastBuilding(Base):
    __tablename__ = "broadcast_buildings"

    broadcast_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("broadcasts.id"), primary_key=True
    )
    building_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("buildings.id"), primary_key=True
    )


class Broadcast(Base):
    __tablename__ = "broadcasts"
    __table_args__ = (
        # One broadcast at a time: two admins cannot start a second sending.
        Index(
            "uq_broadcasts_single_sending",
            "status",
            unique=True,
            postgresql_where=text("status = 'SENDING'"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    author_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    file_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("files.id"))
    status: Mapped[BroadcastStatus] = mapped_column(
        Enum(BroadcastStatus, name="broadcast_status"), nullable=False
    )
    recipients_total: Mapped[int] = mapped_column(Integer, nullable=False)
    delivered_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    author: Mapped[User] = relationship(lazy="selectin")
    buildings: Mapped[list[Building]] = relationship(
        secondary="broadcast_buildings", lazy="selectin", order_by=Building.address
    )
