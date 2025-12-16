from __future__ import annotations

from typing import List

from fastapi import APIRouter, Request

from ..services.graphdb import GraphDBClient
from ..utils.graphdb_exploration_utils import query_species_roles as gxu_query_species_roles

router = APIRouter(prefix="/models/species-roles", tags=["knowledge graph: species-roles"])


@router.get("/", response_model=List[str])
async def list_species_roles(request: Request) -> List[str]:
    client: GraphDBClient | None = getattr(request.app.state, "graphdb", None)
    if not client:
        return []
    try:
        roles = gxu_query_species_roles(client)
        return roles
    except Exception:
        # Return empty list on failure to keep endpoint resilient
        return []
