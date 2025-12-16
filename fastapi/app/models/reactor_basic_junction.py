from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column

from . import V1Base


class ReactorBasicJunction(V1Base):
    __tablename__ = "reactor_basic_junction"

    reactor_id: Mapped[int] = mapped_column(ForeignKey("reactors.id", ondelete="CASCADE"), primary_key=True)
    basic_id: Mapped[int] = mapped_column(ForeignKey("basics.id", ondelete="CASCADE"), primary_key=True)
    association_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
