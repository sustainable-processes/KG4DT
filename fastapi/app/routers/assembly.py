from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, Query, Request

from ..services.graphdb import GraphDBClient
from ..utils.graphdb_exploration_utils import query_ac  # unused import kept for future assembly APIs
from ..utils.graphdb_model_utils import SPARQL_PREFIX
from ..utils import graphdb_exploration_utils as gxu

router = APIRouter(prefix="/api/model/assembly", tags=["assembly"])  # align with Flask paths


@router.get("/list_species_role")
async def list_species_role(request: Request, limit: int = Query(None, ge=0, le=500), offset: int = Query(0, ge=0), order_dir: str = Query("asc")) -> dict:
    """List SpeciesRole names from the knowledge graph (GraphDB).

    Notes:
    - This mirrors the Flask api_assembly_list_species_role endpoint and does not use the SQL database.
    - Query parameters are accepted for future parity but currently only limit/offset slicing is applied.
    - order_dir is accepted (asc|desc) but roles are returned sorted ascending by default, matching Flask behavior.
    """
    client: GraphDBClient | None = getattr(request.app.state, "graphdb", None)
    if not client:
        raise HTTPException(status_code=503, detail="GraphDB client is not available")

    try:
        roles = gxu.query_species_roles(client)
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "Failed to query SpeciesRole from GraphDB", "detail": str(e)})

    # Apply deterministic ordering and optional slicing
    order_dir = (order_dir or "asc").lower()
    if order_dir not in {"asc", "desc"}:
        order_dir = "asc"
    roles_sorted: List[str] = sorted(roles)
    if order_dir == "desc":
        roles_sorted = list(reversed(roles_sorted))

    if offset:
        roles_sorted = roles_sorted[offset:]
    if limit is not None:
        roles_sorted = roles_sorted[:limit]

    return {"species_roles": roles_sorted, "count": len(roles_sorted), "source": "kg"}
