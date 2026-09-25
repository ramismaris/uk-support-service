from sqlalchemy import BigInteger, Boolean, Identity, Text, true
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class Building(Base):
    __tablename__ = "buildings"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    address: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    external_id: Mapped[str | None] = mapped_column(Text, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=true())
