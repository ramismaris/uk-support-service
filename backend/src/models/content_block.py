from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class ContentBlock(Base):
    __tablename__ = "content_blocks"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    data: Mapped[dict] = mapped_column(postgresql.JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    updated_by_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
