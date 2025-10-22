from __future__ import annotations

from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import Session

from ..dependencies import DbSessionDep
from ..models.basic import Basic
from ..schemas.basic import BasicCreate, BasicUpdate, BasicRead

router = APIRouter(prefix="/models/basics", tags=["models", "basics"])


def _pagination_params(limit: Optional[int] = Query(100, ge=0, le=500), offset: Optional[int] = Query(0, ge=0)) -> tuple[int, int]:
    return limit or 100, offset or 0


@router.get("/", response_model=List[BasicRead])
def list_basics(db: DbSessionDep, limit: int = Query(100, ge=0, le=500), offset: int = Query(0, ge=0)):
    q = db.query(Basic).offset(offset)
    if limit:
        q = q.limit(limit)
    return q.all()


@router.get("/{basic_id}", response_model=BasicRead)
def get_basic(basic_id: int, db: DbSessionDep):
    obj = db.get(Basic, basic_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Basic not found")
    return obj


@router.post("/", response_model=BasicRead, status_code=201)
def create_basic(payload: BasicCreate, db: DbSessionDep):
    obj = Basic(
        name=payload.name,
        size=payload.size,
        substance=payload.substance,
        time=payload.time,
        pressure=payload.pressure,
        temperature=payload.temperature,
        structure=payload.structure,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{basic_id}", response_model=BasicRead)
def update_basic(basic_id: int, payload: BasicUpdate, db: DbSessionDep):
    obj: Optional[Basic] = db.query(Basic).get(basic_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Basic not found")

    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(obj, k, v)

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{basic_id}", status_code=204)
def delete_basic(basic_id: int, db: DbSessionDep):
    obj: Optional[Basic] = db.query(Basic).get(basic_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Basic not found")
    db.delete(obj)
    db.commit()
    return None
