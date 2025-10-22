from __future__ import annotations
from fastapi import Request
from starlette import status
from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.engine import Engine

from ..db import get_engine
from ..services.graphdb import GraphDBClient

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/", status_code=status.HTTP_200_OK)
async def health_root() -> dict:
    """Return basic health info without probing dependencies."""
    return {"status": "ok"}


@router.get("/deep", status_code=status.HTTP_200_OK)
async def deep_health(request: Request) -> dict:
    """Deep health check probing DB and GraphDB connectivity."""
    db_ok = False
    try:
        engine: Engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    graph_client: GraphDBClient | None = getattr(request.app.state, "graphdb", None)
    graph_ok = graph_client.ping() if graph_client else False

    return {"status": "ok" if (db_ok and graph_ok) else "degraded", "database": db_ok, "graphdb": graph_ok}
