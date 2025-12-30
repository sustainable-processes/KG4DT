from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, String, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import V1Base


class Project(V1Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint("char_length(name) > 0", name="name_not_empty"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="projects")
    models: Mapped[list["Model"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    experiments: Mapped[list["ExperimentData"]] = relationship(back_populates="project", cascade="all, delete-orphan")
