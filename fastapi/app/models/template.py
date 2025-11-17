from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class Template(Base):
    __tablename__ = "template"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(255), nullable=False)
    reactor_id: Mapped[int] = mapped_column(Integer, ForeignKey("reactor.id", ondelete="CASCADE"), nullable=False)

    def __repr__(self) -> str:
        return f"<Template id={self.id} category={self.category!r} reactor_id={self.reactor_id}>"
