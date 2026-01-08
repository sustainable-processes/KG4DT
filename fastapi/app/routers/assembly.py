from __future__ import annotations

import re
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ..services.graphdb import GraphDBClient
from ..utils import graphdb_exploration_utils as gxu
from ..utils.graphdb_assembly_utils import query_context_template

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


RXN_PATTERN = r"^((\d+ )?.+ \+ )*(\d+ )?.+ > ((\d+ )?.+ \+ )*(\d+ )?.+$"


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
    """
    Validate and augment species_id using reaction expressions.

    Input (POST /validate_species/)
    {
      "species_id": ["A", "B"],
      "stoichiometric": [
        "A + 2 B > C",
        "C + D > 3 E"
      ]
    }
    Output
    {
      "species_id": ["A", "B", "C", "D", "E"]
    }
    """
    out: List[str] = []
    seen = set()

    # Initialize with existing species
    for s in payload.species_id:
        if isinstance(s, str):
            s_norm = s.strip()
            if re.match(r"^[A-Za-z][A-Za-z0-9_]*$", s_norm) and s_norm not in seen:
                seen.add(s_norm)
                out.append(s_norm)

    # Reaction Extraction & Discovery
    for rxn in payload.stoichiometric or []:
        if not isinstance(rxn, str):
            continue
        
        # Pattern Matching for simulation accuracy
        if not re.match(RXN_PATTERN, rxn):
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid reaction format: '{rxn}'. Expected format like '2 A + B > 3 C'"
            )
        
        # Consistency Check / Extraction
        try:
            lhs, rhs = rxn.split(" > ")
            lhs_spcs = [s.strip().split(" ")[-1] for s in lhs.split(" + ")]
            rhs_spcs = [s.strip().split(" ")[-1] for s in rhs.split(" + ")]
            
            for sp in lhs_spcs + rhs_spcs:
                if sp and sp not in seen:
                    # Strict Verification: if not in seen, it is a "discovery"
                    seen.add(sp)
                    out.append(sp)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error parsing reaction '{rxn}': {str(e)}"
            )

    return ValidateSpeciesResponse(species_id=out)


@router.get("/context_template")
def list_context_templates(request: Request):
    """List all context templates from the Knowledge Graph."""
    client: GraphDBClient | None = getattr(request.app.state, "graphdb", None)
    if not client:
        raise HTTPException(status_code=503, detail="Knowledge Graph client is not configured")

    try:
        data = query_context_template(client)
        return {
            "context_templates": data,
            "count": len(data),
            "source": "kg"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "Failed to query context templates", "detail": str(e)})


@router.get("/pheno/rxn")
async def get_rxn(request: Request):
    """Return ReactionPhenomenon names from the knowledge graph.

    This GET endpoint accepts no parameters or body and simply lists reactions
    discovered in GraphDB.
    """
    client: GraphDBClient | None = getattr(request.app.state, "graphdb", None)
    if not client:
        raise HTTPException(status_code=503, detail="GraphDB client is not available")

    data = gxu.query_rxn(client)
    if isinstance(data, dict) and data.get("error") == "NotImplemented":
        raise HTTPException(status_code=501, detail=data)
    # Always return 200 with the list (possibly empty)
    return data
