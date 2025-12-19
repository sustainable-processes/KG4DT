from __future__ import annotations
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Integer,
    String,
    ForeignKey,
    TIMESTAMP,
    func,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, CITEXT, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import V1Base


# Enums as SQLAlchemy Enum types (Postgres native enums will be created by Alembic)
from sqlalchemy import Enum as SAEnum


BasicMatterType = SAEnum("steam", "solid", "gas", name="basic_matter_type", native_enum=True)
BasicUsageEnum = SAEnum("inlet", "outlet", "utilities", name="basic_usage", native_enum=True)


class User(V1Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    projects: Mapped[list[Project]] = relationship(back_populates="user", cascade="all, delete-orphan")  # type: ignore


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
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped[User] = relationship(back_populates="projects")  # type: ignore
    models: Mapped[list[Model]] = relationship(back_populates="project", cascade="all, delete-orphan")  # type: ignore
    experiments: Mapped[list[ExperimentData]] = relationship(back_populates="project", cascade="all, delete-orphan")  # type: ignore


class ExperimentData(V1Base):
    __tablename__ = "experiment_data"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    data: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    project: Mapped[Project] = relationship(back_populates="experiments")  # type: ignore


class Model(V1Base):
    __tablename__ = "models"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    mt: Mapped[list[str]] = mapped_column(ARRAY(String()))
    me: Mapped[list[str]] = mapped_column(ARRAY(String()))
    laws: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    project: Mapped[Project] = relationship(back_populates="models")  # type: ignore


class Reactor(V1Base):
    __tablename__ = "reactors"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    number_of_input: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    number_of_output: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    # Icon column (renamed from icon_url via Alembic migration)
    icon: Mapped[str | None] = mapped_column(String(255))
    reactor: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    chemistry: Mapped[dict | None] = mapped_column(JSONB)
    kinetics: Mapped[dict | None] = mapped_column(JSONB)

    basics: Mapped[list[Basic]] = relationship(
        secondary="reactor_basic_junction", back_populates="reactors"
    )  # type: ignore


class Basic(V1Base):
    __tablename__ = "basics"
    __table_args__ = (
        CheckConstraint("char_length(name) > 0", name="name_not_empty"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(BasicMatterType, nullable=False)
    usage: Mapped[str] = mapped_column(BasicUsageEnum, nullable=False)
    structure: Mapped[str | None] = mapped_column(String(100))
    phase: Mapped[str | None] = mapped_column(String(50))
    operation: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    reactors: Mapped[list[Reactor]] = relationship(
        secondary="reactor_basic_junction", back_populates="basics"
    )  # type: ignore


class ReactorBasicJunction(V1Base):
    __tablename__ = "reactor_basic_junction"

    reactor_id: Mapped[int] = mapped_column(ForeignKey("reactors.id", ondelete="CASCADE"), primary_key=True)
    basic_id: Mapped[int] = mapped_column(ForeignKey("basics.id", ondelete="CASCADE"), primary_key=True)
    association_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)


class Category(V1Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)


class Template(V1Base):
    __tablename__ = "templates"
    __table_args__ = (
        UniqueConstraint("category_id", "reactor_id", name="uq_templates_category_reactor"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False)
    reactor_id: Mapped[int] = mapped_column(ForeignKey("reactors.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
