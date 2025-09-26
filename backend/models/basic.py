from sqlalchemy import Integer, String, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column

from . import Base


class Basic(Base):
    __tablename__ = "basic"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    size: Mapped[float | None] = mapped_column(Float, nullable=True)
    substance: Mapped[str | None] = mapped_column(String(255), nullable=True)
    time: Mapped[float | None] = mapped_column(Float, nullable=True)
    pressure: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    structure: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<Basic id={self.id} name={self.name!r}>"