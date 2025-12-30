from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, TIMESTAMP, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from . import V1Base


class Template(V1Base):
    __tablename__ = "templates"
    __table_args__ = (
        UniqueConstraint("category_id", "reactor_id", name="uq_templates_category_reactor"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False)
    reactor_id: Mapped[int] = mapped_column(ForeignKey("reactors.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
