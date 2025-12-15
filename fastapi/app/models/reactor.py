import datetime as dt

from sqlalchemy import Integer, String, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class Reactor(Base):
    __tablename__ = "reactor"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    number_of_input: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # renamed: number_of_output -> number_of_utility_input
    number_of_utility_input: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_date: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=dt.datetime.utcnow, nullable=False
    )
    icon: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # renamed: species -> json_data (generic JSON container)
    json_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # new JSON columns
    chemistry: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    kinetics: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<Reactor id={self.id} name={self.name!r}>" 
