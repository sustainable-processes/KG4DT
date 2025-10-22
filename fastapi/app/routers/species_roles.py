from __future__ import annotations

from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException, Query

from ..dependencies import DbSessionDep
from ..models.species_role import SpeciesRole
from ..schemas.species_role import SpeciesRoleCreate, SpeciesRoleUpdate, SpeciesRoleRead

router = APIRouter(prefix="/models/species-roles", tags=["species_roles"])


@router.get("/", response_model=List[SpeciesRoleRead])
def list_species_roles(db: DbSessionDep, limit: int = Query(100, ge=0, le=500), offset: int = Query(0, ge=0), order_by: str = Query("id"), order_dir: str = Query("asc")):
    allowed_fields = {"id", "name", "attribute"}
    if order_by not in allowed_fields:
        order_by = "id"
    order_dir = order_dir.lower()
    if order_dir not in {"asc", "desc"}:
        order_dir = "asc"

    q = db.query(SpeciesRole)
    col = getattr(SpeciesRole, order_by)
    q = q.order_by(col.desc() if order_dir == "desc" else col.asc())
    q = q.offset(offset)
    if limit:
        q = q.limit(limit)
    return q.all()


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
