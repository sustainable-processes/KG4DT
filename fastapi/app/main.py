from __future__ import annotations

import logging
import logging.config
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .settings import get_settings
from .services.graphdb import GraphDBClient, GraphDBConfig

# Initialize SQLAlchemy for the FastAPI backend (independent from Flask)
from .db import init_db

def _ensure_root_logging_configured() -> None:
    """Ensure the root logger prints to stdout at INFO level.

    Under Uvicorn's default logging, only the `uvicorn.*` loggers have handlers.
    Our module loggers (e.g., fastapi.app.routers.templates) may be silent unless
    the root logger has a StreamHandler. Configure it only if no handlers exist
    to avoid duplicating Uvicorn's setup.
    """
    root = logging.getLogger()
    if root.handlers:
        return
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "()": "uvicorn.logging.DefaultFormatter",
                    "fmt": "%(levelprefix)s %(message)s",
                }
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "stream": "ext://sys.stdout",
                }
            },
            "root": {"handlers": ["default"], "level": "INFO"},
        }
    )


_ensure_root_logging_configured()

logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    openapi_tags=[
        {"name": "health"},
        {"name": "assembly"},
        {"name": "assembly: projects"},
        {"name": "assembly: reactors"},
        {"name": "assembly: templates"},
        {"name": "assembly: kg_components"},
        {"name": "exploration"},
        {"name": "exploration: models"},
        {"name": "exploration: experiment data"},
        {"name": "calibration"},
        {"name": "v1: assembly"},
        {"name": "v1: assembly: projects"},
        {"name": "v1: assembly: reactors"},
        {"name": "v1: assembly: templates"},
        {"name": "v1: exploration"},
        {"name": "v1: exploration: models"},
        {"name": "v1: exploration: experiment data"},
        {"name": "v1: calibration"},
        {"name": "v1: users"},
        {"name": "v1: basics"},
        {"name": "v1: categories"},
        {"name": "v1: experiment_data"},
        {"name": "v1: kg_components"},
        {"name": "knowledge graph: model"},
        {"name": "knowledge_graph"},
    ],
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
from .routers import kg_model as model_router  # noqa: E402
from .routers import exploration as exploration_router  # noqa: E402
from .routers import info as info_router  # noqa: E402
from .routers import calibration as calibration_router  # noqa: E402
from .routers import assembly as assembly_router  # noqa: E402
# v1 routers (plural snake_case schema)
from .routers import users as v1_users_router  # noqa: E402
from .routers import projects as v1_projects_router  # noqa: E402
from .routers import reactors as v1_reactors_router  # noqa: E402
from .routers import basics as v1_basics_router  # noqa: E402
from .routers import categories as v1_categories_router  # noqa: E402
from .routers import templates as v1_templates_router  # noqa: E402
from .routers import experiment_data as v1_experiment_router  # noqa: E402
from .routers import models as v1_models_router  # noqa: E402
# translation tools
from .routers import translation as v1_translation_router  # noqa: E402
from .routers import kg_components as v1_kg_components_router  # noqa: E402

# Exploration and Calibration (versioned and unversioned)
for prefix in ["/api/v1", "/api"]:
    v = "v1: " if "v1" in prefix else ""
    app.include_router(exploration_router.router, prefix=f"{prefix}/exploration", tags=[f"{v}exploration"])
    app.include_router(info_router.router, prefix=f"{prefix}/exploration", tags=[f"{v}exploration"])
    app.include_router(calibration_router.router, prefix=f"{prefix}/calibration", tags=[f"{v}calibration"])
    app.include_router(v1_models_router.router, prefix=f"{prefix}/exploration/models", tags=[f"{v}exploration: models"])
    app.include_router(v1_experiment_router.router, prefix=f"{prefix}/exploration/experiment_data", tags=[f"{v}exploration: experiment data"])

app.include_router(health_router.router)
app.include_router(model_router.router)

# Assembly endpoints (versioned and unversioned)
for prefix in ["/api/v1/assembly", "/api/assembly"]:
    v = "v1: " if "v1" in prefix else ""
    app.include_router(assembly_router.router, prefix=prefix, tags=[f"{v}assembly"])
    app.include_router(v1_projects_router.router, prefix=f"{prefix}/projects", tags=[f"{v}assembly: projects"])
    app.include_router(v1_projects_router.download_router, prefix=f"{prefix}/download/projects", tags=[f"{v}assembly: projects"])
    app.include_router(v1_reactors_router.router, prefix=f"{prefix}/reactors", tags=[f"{v}assembly: reactors"])
    app.include_router(v1_templates_router.router, prefix=f"{prefix}/templates", tags=[f"{v}assembly: templates"])

# Other endpoints with v1 and non-versioned duplicates
for prefix in ["/api/v1", "/api"]:
    app.include_router(v1_users_router.router, prefix=f"{prefix}/users", tags=["v1: users" if "v1" in prefix else "users"])
    app.include_router(v1_basics_router.router, prefix=f"{prefix}/basics", tags=["v1: basics" if "v1" in prefix else "basics"])
    app.include_router(v1_categories_router.router, prefix=f"{prefix}/categories", tags=["v1: categories" if "v1" in prefix else "categories"])
    app.include_router(v1_experiment_router.router, prefix=f"{prefix}/experiment_data", tags=["v1: experiment_data" if "v1" in prefix else "experiment_data"])
    
    if prefix == "/api/v1":
        app.include_router(v1_kg_components_router.router, prefix=f"{prefix}/kg_components", tags=["v1: kg_components"])
    else:
        app.include_router(v1_kg_components_router.router, prefix=f"{prefix}/assembly/kg_components", tags=["assembly: kg_components"])

# translation tools
app.include_router(v1_translation_router.router)
