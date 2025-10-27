from __future__ import annotations

import logging
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .settings import get_settings
from .services.graphdb import GraphDBClient, GraphDBConfig

# Initialize SQLAlchemy for the FastAPI backend (independent from Flask)
from .db import init_db

logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)

# CORS — default to localhost-only; configure via FASTAPI_CORS_ORIGINS if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    # Initialize SQLAlchemy engine & session factory via fastapi.app.db
    try:
        init_db(echo=settings.database_echo, settings=settings)
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.exception("Failed to initialize database: %s", e)
        # We don't crash the server at startup here, but DB-dependent endpoints will fail.

    # Initialize GraphDB client and attach to app state
    cfg = GraphDBConfig(
        base_url=settings.graphdb_base_url,
        repository=settings.graphdb_repository,
        username=settings.graphdb_username,
        password=settings.graphdb_password,
        timeout_seconds=settings.graphdb_timeout_seconds,
    )
    app.state.graphdb = GraphDBClient(cfg)


@app.get("/")
async def root() -> dict:
    return {"app": settings.app_name, "status": "running"}


# Routers
from .routers import health as health_router  # noqa: E402
from .routers import basics as basics_router  # noqa: E402
from .routers import projects as projects_router  # noqa: E402
from .routers import reactors as reactors_router  # noqa: E402
from .routers import species_roles as species_roles_router  # noqa: E402
from .routers import model as model_router  # noqa: E402
from .routers import exploration as exploration_router  # noqa: E402

app.include_router(health_router.router)
app.include_router(basics_router.router)
app.include_router(projects_router.router)
app.include_router(reactors_router.router)
app.include_router(species_roles_router.router)
app.include_router(model_router.router)
app.include_router(exploration_router.router)
