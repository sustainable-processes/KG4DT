from __future__ import annotations

import re
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ..services.graphdb import GraphDBClient
from ..utils import graphdb_exploration_utils as gxu

router = APIRouter()


class ValidateSpeciesRequest(BaseModel):
    stoichiometric: List[str] = Field(default_factory=list, description="List of stoichiometric strings, e.g. 'A + B = C'")
    species_id: List[str] = Field(default_factory=list, description="Initial list of species IDs")


class ValidateSpeciesResponse(BaseModel):
    species_id: List[str]


class SpeciesRolesResponse(BaseModel):
    species_roles: List[str]
    count: int
    source: str = "kg"


_LEADING_COEFF_RE = re.compile(r"^\s*(?:\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*")


def _normalize_token(token: str) -> str | None:
    """Normalize a stoichiometric token to a species name."""
    if token is None:
        return None
    s = token.strip()
    if not s:
        return None
    if s.startswith("(") and s.endswith(")"):
        s = s[1:-1].strip()
    s = _LEADING_COEFF_RE.sub("", s, count=1)
    s = s.strip()
    if not s:
        return None
    if not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", s):
        return None
    return s


@router.get("/species_roles", response_model=SpeciesRolesResponse)
async def list_species_roles(
    request: Request,
    limit: Optional[int] = Query(None, ge=0, le=500),
    offset: int = Query(0, ge=0),
    order_dir: str = Query("asc")
) -> SpeciesRolesResponse:
    """List SpeciesRole names from the knowledge graph (GraphDB)."""
    client: GraphDBClient | None = getattr(request.app.state, "graphdb", None)
    if not client:
        raise HTTPException(status_code=503, detail="GraphDB client is not available")

    try:
        roles = gxu.query_species_roles(client)
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "Failed to query SpeciesRole from GraphDB", "detail": str(e)})

    order_dir = (order_dir or "asc").lower()
    if order_dir not in {"asc", "desc"}:
        order_dir = "asc"
    roles_sorted: List[str] = sorted(roles)
    if order_dir == "desc":
        roles_sorted = list(reversed(roles_sorted))

    total_count = len(roles_sorted)

    if offset:
        roles_sorted = roles_sorted[offset:]
    if limit is not None:
        roles_sorted = roles_sorted[:limit]

    return SpeciesRolesResponse(species_roles=roles_sorted, count=total_count, source="kg")


@router.post("/validate_species/", response_model=ValidateSpeciesResponse)
def validate_species(payload: ValidateSpeciesRequest) -> ValidateSpeciesResponse:
    """Validate and augment species_id using stoichiometric expressions."""
    out: List[str] = []
    seen = set()

    for s in payload.species_id:
        if isinstance(s, str):
            s_norm = s.strip()
            if re.match(r"^[A-Za-z][A-Za-z0-9_]*$", s_norm) and s_norm not in seen:
                seen.add(s_norm)
                out.append(s_norm)

    for expr in payload.stoichiometric or []:
        if not isinstance(expr, str):
            continue
        parts = re.split(r"[=+]", expr)
        for part in parts:
            sp = _normalize_token(part)
            if sp and sp not in seen:
                seen.add(sp)
                out.append(sp)

    return ValidateSpeciesResponse(species_id=out)
