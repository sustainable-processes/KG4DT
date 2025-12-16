from __future__ import annotations

from fastapi import APIRouter, Request
from starlette import status

from ..services.graphdb import GraphDBClient
from ..utils.graphdb_model_utils import query_var, query_unit

router = APIRouter(prefix="/api/model", tags=["knowledge graph: model"])  # KG-backed endpoints


@router.get("/var", status_code=status.HTTP_200_OK)
async def get_model_var(request: Request) -> dict:
    client: GraphDBClient | None = getattr(request.app.state, "graphdb", None)
    if not client:
        return {"error": "GraphDB client is not initialized"}
    try:
        data = query_var(client)
        return data
    except Exception as e:
        return {"error": f"Failed to query variables from GraphDB: {e}"}


@router.get("/unit", status_code=status.HTTP_200_OK)
async def get_model_unit(request: Request) -> dict:
    client: GraphDBClient | None = getattr(request.app.state, "graphdb", None)
    if not client:
        return {"error": "GraphDB client is not initialized"}
    try:
        data = query_unit(client)
        return data
    except Exception as e:
        return {"error": f"Failed to query units from GraphDB: {e}"}
