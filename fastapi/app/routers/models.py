from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, Query

from ..dependencies import DbSessionDep
from .. import models as m
from ..schemas.models import ModelCreate, ModelRead, ModelUpdate, ModelListItem

router = APIRouter(prefix="/api/v1/models", tags=["v1: models"])
# Non-versioned duplicate under /api/models
router_nv = APIRouter(prefix="/api/models", tags=["models"])


def _get_or_404(db: DbSessionDep, model_id: int) -> m.Model:
    obj = db.get(m.Model, model_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Model not found")
    return obj


@router.get("/", response_model=List[ModelListItem])
def list_models(
    db: DbSessionDep,
    project_id: int = Query(..., ge=1),
    limit: int = Query(100, ge=0, le=500),
    offset: int = Query(0, ge=0),
):
    # Ensure project exists
    project = db.get(m.Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    q = db.query(m.Model).filter(m.Model.project_id == project_id)
    q = q.order_by(m.Model.updated_at.desc(), m.Model.id.desc())
    if offset:
        q = q.offset(offset)
    if limit:
        q = q.limit(limit)
    # Returning full Model rows; response_model will serialize only id and name
    return q.all()


@router_nv.get("/", response_model=List[ModelListItem])
def list_models_nv(
    db: DbSessionDep,
    project_id: int = Query(..., ge=1),
    limit: int = Query(100, ge=0, le=500),
    offset: int = Query(0, ge=0),
):
    return list_models(db=db, project_id=project_id, limit=limit, offset=offset)


@router.get("/{model_id}", response_model=ModelRead)
def get_model(model_id: int, db: DbSessionDep):
    return _get_or_404(db, model_id)


@router_nv.get("/{model_id}", response_model=ModelRead)
def get_model_nv(model_id: int, db: DbSessionDep):
    return get_model(model_id, db)


@router.post("/", response_model=ModelRead, status_code=201)
def create_model(payload: ModelCreate, db: DbSessionDep):
    # Ensure project exists
    if not db.get(m.Project, payload.project_id):
        raise HTTPException(status_code=400, detail="Invalid project_id")
    obj = m.Model(
        project_id=payload.project_id,
        name=payload.name,
        mt=payload.mt or [],
        me=payload.me or [],
        laws=payload.laws or {},
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router_nv.post("/", response_model=ModelRead, status_code=201)
def create_model_nv(payload: ModelCreate, db: DbSessionDep):
    return create_model(payload, db)


@router.patch("/{model_id}", response_model=ModelRead)
def update_model(model_id: int, payload: ModelUpdate, db: DbSessionDep):
    obj = _get_or_404(db, model_id)
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(obj, k, v)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router_nv.patch("/{model_id}", response_model=ModelRead)
def update_model_nv(model_id: int, payload: ModelUpdate, db: DbSessionDep):
    return update_model(model_id, payload, db)


@router.delete("/{model_id}", status_code=204)
def delete_model(model_id: int, db: DbSessionDep):
    obj = _get_or_404(db, model_id)
    db.delete(obj)
    db.commit()
    return None


@router_nv.delete("/{model_id}", status_code=204)
def delete_model_nv(model_id: int, db: DbSessionDep):
    return delete_model(model_id, db)
