import os
from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, DeclarativeBase

# Singletons created on init_app
_engine = None
_SessionFactory = None


class Base(DeclarativeBase):
    pass


def _build_database_url() -> Optional[str]:
    """Resolve a SQLAlchemy DATABASE URL from environment variables.
    Priority:
      1) DATABASE_URL
      2) postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}
    """
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    user = os.getenv("DB_USER", "postgres")
    pwd = os.getenv("DB_PASSWORD", "postgres")
    name = os.getenv("DB_NAME")
    if not name:
        return None
    return f"postgresql://{user}:{pwd}@{host}:{port}/{name}"


def init_app(app=None, *, echo: bool = False):
    """Initialize the SQLAlchemy engine/session using env configuration.

    Call this once during app startup. Safe to call multiple times; subsequent
    calls are no-ops.
    """
    global _engine, _SessionFactory
    if _engine is not None:
        return

    db_url = _build_database_url()
    if not db_url:
        raise RuntimeError("DATABASE_URL or DB_* env vars are not set. Cannot initialize database engine.")

    _engine = create_engine(db_url, echo=echo, future=True)
    _SessionFactory = scoped_session(sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True))

    # Import models so that Base.metadata knows about them before create_all
    from .project import Project  # noqa: F401
    from .basic import Basic      # noqa: F401

    # Optionally create tables on startup (idempotent)
    try:
        Base.metadata.create_all(_engine)
    except Exception as e:
        # Don't crash the app on startup if DB is unavailable; raise to caller to handle
        raise


def get_engine():
    if _engine is None:
        raise RuntimeError("Database engine is not initialized. Call backend.models.init_app(app) first.")
    return _engine


def get_session():
    if _SessionFactory is None:
        raise RuntimeError("Session factory is not initialized. Call backend.models.init_app(app) first.")
    return _SessionFactory()
