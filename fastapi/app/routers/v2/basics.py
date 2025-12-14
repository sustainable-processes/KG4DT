from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from ...dependencies import DbSessionDep
from ...models.v2 import models as m
from ...schemas.v2.basics import BasicCreate, BasicRead, BasicUpdate
from ...schemas.v2.types import BasicMatterType, BasicUsage

router = APIRouter(prefix="/api/v2/basics", tags=["v2: basics"])


def _get_basic_or_404(db: DbSessionDep, basic_id: int) -> m.Basic:
    obj = db.get(m.Basic, basic_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Basic not found")
    return obj


@router.get("/", response_model=List[BasicRead])
def list_basics(
    db: DbSessionDep,
    type: Optional[BasicMatterType] = Query(None),
    usage: Optional[BasicUsage] = Query(None),
    limit: int = Query(100, ge=0, le=500),
    offset: int = Query(0, ge=0),
):
    q = db.query(m.Basic)
    if type is not None:
        q = q.filter(m.Basic.type == type.value)
    if usage is not None:
        q = q.filter(m.Basic.usage == usage.value)
    q = q.order_by(m.Basic.name.asc())
    if offset:
        q = q.offset(offset)
    if limit:
        q = q.limit(limit)
    return q.all()


@router.get("/{basic_id}", response_model=BasicRead)
def get_basic(basic_id: int, db: DbSessionDep):
    return _get_basic_or_404(db, basic_id)


@router.post("/", response_model=BasicRead, status_code=201)
def create_basic(payload: BasicCreate, db: DbSessionDep):
    obj = m.Basic(
        name=payload.name,
        type=payload.type.value,
        usage=payload.usage.value,
        structure=payload.structure,
        phase=payload.phase,
        operation=payload.operation,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{basic_id}", response_model=BasicRead)
def update_basic(basic_id: int, payload: BasicUpdate, db: DbSessionDep):
    obj = _get_basic_or_404(db, basic_id)
    data = payload.model_dump(exclude_unset=True)
    # Convert enums to str values
    if "type" in data and data["type"] is not None:
        data["type"] = data["type"].value
    if "usage" in data and data["usage"] is not None:
        data["usage"] = data["usage"].value
    for k, v in data.items():
        setattr(obj, k, v)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{basic_id}", status_code=204)
def delete_basic(basic_id: int, db: DbSessionDep):
    obj = _get_basic_or_404(db, basic_id)
    db.delete(obj)
    db.commit()
    return None
