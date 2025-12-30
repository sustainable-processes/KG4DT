from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, String, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import V1Base


class Model(V1Base):
    __tablename__ = "models"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    mt: Mapped[list[str]] = mapped_column(ARRAY(String()))
    me: Mapped[list[str]] = mapped_column(ARRAY(String()))
    laws: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    project: Mapped["Project"] = relationship(back_populates="models")
