from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Text,
    UniqueConstraint,
    false,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class Residence(Base):
    __tablename__ = "residences"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "building_id", "apartment", name="uq_residences_user_building_apartment"
        ),
        Index(
            "uq_residences_primary_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("is_primary"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    building_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("buildings.id"), nullable=False)
    apartment: Mapped[str] = mapped_column(Text, nullable=False)
    account_number: Mapped[str | None] = mapped_column(Text)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
