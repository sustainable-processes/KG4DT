from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, String, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Enum as SAEnum

from . import V1Base


BasicMatterType = SAEnum("stream", "solid", "gas", name="basic_matter_type", native_enum=True)
BasicUsageEnum = SAEnum("inlet", "outlet", "utilities", name="basic_usage", native_enum=True)


class Basic(V1Base):
    __tablename__ = "basics"
    __table_args__ = (
        CheckConstraint("char_length(name) > 0", name="name_not_empty"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(BasicMatterType, nullable=True)
    usage: Mapped[str] = mapped_column(BasicUsageEnum, nullable=False)
    structure: Mapped[dict | None] = mapped_column(JSONB)
    phase: Mapped[dict | None] = mapped_column(JSONB)
    operation: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    reactors: Mapped[list["Reactor"]] = relationship(secondary="reactor_basic_junction", back_populates="basics")
