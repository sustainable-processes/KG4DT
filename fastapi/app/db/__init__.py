from typing import Optional

from sqlalchemy import create_engine, text, inspect
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

    # Import v2 models so that their metadata is registered before create_all
    # (imports are intentionally unused; they ensure model classes are imported)
    from ..models.user import User  # noqa: F401
    from ..models.project import Project  # noqa: F401
    from ..models.experiment_data import ExperimentData  # noqa: F401
    from ..models.model import Model  # noqa: F401
    from ..models.reactor import Reactor  # noqa: F401
    from ..models.basic import Basic  # noqa: F401
    from ..models.reactor_basic_junction import ReactorBasicJunction  # noqa: F401
    from ..models.category import Category  # noqa: F401
    from ..models.template import Template  # noqa: F401

    # Create tables idempotently for both legacy Base and v2 V1Base
    Base.metadata.create_all(_engine)
    try:
        # V1Base is the declarative base used by the v2 relational schema
        from ..models import V1Base

        V1Base.metadata.create_all(_engine)
    except Exception:
        # If models package is unavailable or misconfigured, skip silently
        pass

    # Perform lightweight, idempotent startup migrations to keep legacy DBs in sync
    _apply_startup_migrations()


def get_engine() -> "Engine":
    if _engine is None:
        raise RuntimeError("Database engine is not initialized. Call fastapi.app.db.init_db() first.")
    return _engine



def get_session():
    if _SessionFactory is None:
        raise RuntimeError("Session factory is not initialized. Call fastapi.app.db.init_db() first.")
    return _SessionFactory()


def _apply_startup_migrations() -> None:
    """Best-effort migrations for legacy databases.

    This ensures the Reactor table has the new columns and names without requiring
    manual SQL. It is safe to run on every startup and only applies changes when
    needed.

    What it does:
    - Rename species -> json_data
    - Rename number_of_output -> number_of_utility_input
    - Add chemistry (JSON/JSONB) if missing
    - Add phenomenon (JSON/JSONB) if missing
    """
    global _engine
    if _engine is None:
        return

    engine = _engine
    insp = inspect(engine)

    # If reactor table doesn't exist (fresh DB), nothing to migrate
    if not insp.has_table("reactor"):
        return

    try:
        columns = {col["name"] for col in insp.get_columns("reactor")}
    except Exception:
        # If inspection fails, skip migrations silently
        return

    is_pg = (getattr(engine.dialect, "name", "").lower() == "postgresql")
    json_type = "JSONB" if is_pg else "JSON"

    # Helper to execute DDL safely
    def exec_ddl(sql: str) -> None:
        try:
            with engine.begin() as conn:
                conn.execute(text(sql))
        except Exception:
            # Ignore failures to keep startup resilient (e.g., column already renamed)
            pass

    # 1) Rename columns if legacy names present
    if "species" in columns and "json_data" not in columns:
        # Standard SQL RENAME COLUMN (supported by PostgreSQL >= 9.1, SQLite >= 3.25, MySQL 8.0+)
        exec_ddl("ALTER TABLE reactor RENAME COLUMN species TO json_data;")
        # refresh column set after potential change
        try:
            columns = {col["name"] for col in insp.get_columns("reactor")}
        except Exception:
            pass

    if "number_of_output" in columns and "number_of_utility_input" not in columns:
        exec_ddl("ALTER TABLE reactor RENAME COLUMN number_of_output TO number_of_utility_input;")
        try:
            columns = {col["name"] for col in insp.get_columns("reactor")}
        except Exception:
            pass

    # 2) Add JSON columns if missing
    if "chemistry" not in columns:
        exec_ddl(f"ALTER TABLE reactor ADD COLUMN chemistry {json_type};")
        try:
            columns = {col["name"] for col in insp.get_columns("reactor")}
        except Exception:
            pass

    if "phenomenon" not in columns:
        exec_ddl(f"ALTER TABLE reactor ADD COLUMN phenomenon {json_type};")