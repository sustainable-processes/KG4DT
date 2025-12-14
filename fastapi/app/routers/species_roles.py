from __future__ import annotations

from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from ..dependencies import DbSessionDep
from ..models.species_role import SpeciesRole
from ..schemas.species_role import SpeciesRoleCreate, SpeciesRoleUpdate, SpeciesRoleRead
from ..services.graphdb import GraphDBClient
from ..utils import graphdb_exploration_utils as gxu

router = APIRouter(prefix="/models/species-roles", tags=["species_roles"])


@router.get("/", response_model=List[str])
def list_species_roles(request: Request):
    """List SpeciesRole names from the knowledge graph (GraphDB), ascending by name.

    Returns a plain array of strings (role names). No id, no attribute, no pagination.
    """

    client: GraphDBClient | None = getattr(request.app.state, "graphdb", None)
    if not client:
        raise HTTPException(status_code=503, detail="GraphDB client is not available")

    try:
        roles = gxu.query_species_roles(client)  # already unique and sorted ascending
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "Failed to query SpeciesRole from GraphDB", "detail": str(e)})

    return roles


@router.get("/{role_id}", response_model=SpeciesRoleRead)
def get_species_role(role_id: int, db: DbSessionDep):
    obj = db.get(SpeciesRole, role_id)
    if not obj:
        raise HTTPException(status_code=404, detail="SpeciesRole not found")
    return obj


@router.post("/", response_model=SpeciesRoleRead, status_code=201)
def create_species_role(payload: SpeciesRoleCreate, db: DbSessionDep):
    obj = SpeciesRole(name=payload.name, attribute=payload.attribute)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{role_id}", response_model=SpeciesRoleRead)
def update_species_role(role_id: int, payload: SpeciesRoleUpdate, db: DbSessionDep):
    obj: Optional[SpeciesRole] = db.get(SpeciesRole, role_id)
    if not obj:
        raise HTTPException(status_code=404, detail="SpeciesRole not found")

    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(obj, k, v)

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{role_id}", status_code=204)
def delete_species_role(role_id: int, db: DbSessionDep):
    obj: Optional[SpeciesRole] = db.get(SpeciesRole, role_id)
    if not obj:
        raise HTTPException(status_code=404, detail="SpeciesRole not found")
    db.delete(obj)
    db.commit()
    return None
