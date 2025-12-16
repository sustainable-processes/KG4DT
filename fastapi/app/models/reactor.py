from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Integer, String, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import V1Base


class Reactor(V1Base):
    __tablename__ = "reactors"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    number_of_input: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    number_of_output: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    icon_url: Mapped[str | None] = mapped_column(String(255))
    reactor: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    chemistry: Mapped[dict | None] = mapped_column(JSONB)
    kinetics: Mapped[dict | None] = mapped_column(JSONB)

    basics: Mapped[list["Basic"]] = relationship(secondary="reactor_basic_junction", back_populates="reactors")
