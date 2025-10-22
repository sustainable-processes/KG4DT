from typing import List, Optional
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings, sourced from environment variables.

    Notes:
    - Single source of truth: use this Settings class (via get_settings()) everywhere rather than os.getenv.
    - Database connection for FastAPI is configured here and consumed by fastapi.app.db.
    - GraphDB settings configure the SPARQL endpoint connection.
    - Use FASTAPI_* prefix for these settings to avoid collisions with other app envs.
    """

    app_name: str = "KG4DT FastAPI"
    debug: bool = False

    # CORS
    cors_origins: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]
    )

    # Database
    database_echo: bool = False  # SQLAlchemy echo (logs SQL queries)
    database_url: Optional[str] = None
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "postgres"
    db_password: str = "postgres"
    db_name: Optional[str] = None

    # GraphDB / SPARQL
    graphdb_base_url: str = "http://localhost:7200"
    graphdb_repository: str = "kg4dt"
    graphdb_username: Optional[str] = None
    graphdb_password: Optional[str] = None
    graphdb_timeout_seconds: int = 15

    class Config:
        # Always load the FastAPI service env from fastapi/.env regardless of the working directory
        env_file = str(Path(__file__).resolve().parent.parent / ".env")
        env_prefix = "FASTAPI_"
        extra = "allow"


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance (single source of configuration)."""
    return Settings()
