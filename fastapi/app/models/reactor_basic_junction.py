from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, TIMESTAMP, func, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from . import V1Base


class ReactorBasicJunction(V1Base):
    __tablename__ = "reactor_basic_junction"

    # Allow duplicate associations of the same (reactor_id, basic_id) pair by
    # introducing a surrogate primary key `id` instead of a composite PK.
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    reactor_id: Mapped[int] = mapped_column(ForeignKey("reactors.id", ondelete="CASCADE"), nullable=False)
    basic_id: Mapped[int] = mapped_column(ForeignKey("basics.id", ondelete="CASCADE"), nullable=False)
    association_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
