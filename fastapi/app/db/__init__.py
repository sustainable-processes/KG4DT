from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, scoped_session, sessionmaker

from ..settings import Settings, get_settings

# Singletons created on init_db
_engine = None
_SessionFactory = None


class Base(DeclarativeBase):
    pass


def _build_database_url(settings: Settings) -> Optional[str]:
    """Resolve a SQLAlchemy DATABASE URL for the FastAPI backend from Settings.

    Priority:
      1) settings.database_url (FASTAPI_DATABASE_URL)
      2) postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}
    """
    if settings.database_url:
        return settings.database_url
    if not settings.db_name:
        return None
    host = settings.db_host
    port = settings.db_port
    user = settings.db_user
    pwd = settings.db_password
    name = settings.db_name
    return f"postgresql://{user}:{pwd}@{host}:{port}/{name}"


def init_db(*, echo: bool | None = None, settings: Settings | None = None):
    """Initialize the SQLAlchemy engine/session for the FastAPI backend.

    Safe to call multiple times; subsequent calls are no-ops.
    """
    global _engine, _SessionFactory
    if _engine is not None:
        return

    settings = settings or get_settings()
    db_url = _build_database_url(settings)
    if not db_url:
        raise RuntimeError(
            "FASTAPI_DATABASE_URL or FASTAPI_DB_* env vars are not set. Cannot initialize database engine."
        )

    echo_val = settings.database_echo if echo is None else echo
    _engine = create_engine(db_url, echo=echo_val, future=True)
    _SessionFactory = scoped_session(sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True))

    # Import models so that Base.metadata knows about them before create_all
    from ..models.basic import Basic  # noqa: F401
    from ..models.project import Project  # noqa: F401
    from ..models.reactor import Reactor  # noqa: F401
    from ..models.species_role import SpeciesRole  # noqa: F401

    # Create tables idempotently
    Base.metadata.create_all(_engine)


def get_engine() -> "Engine":
    if _engine is None:
        raise RuntimeError("Database engine is not initialized. Call fastapi.app.db.init_db() first.")
    return _engine



def get_session():
    if _SessionFactory is None:
        raise RuntimeError("Session factory is not initialized. Call fastapi.app.db.init_db() first.")
    return _SessionFactory()