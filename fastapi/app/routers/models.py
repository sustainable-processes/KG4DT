from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, Query

from ..dependencies import DbSessionDep
from .. import models as m
from ..schemas.models import ModelCreate, ModelRead, ModelUpdate, ModelListItem
from ..utils.db import apply_updates, verify_project_ownership

router = APIRouter()


def _get_or_404(db: DbSessionDep, model_id: int) -> m.Model:
    obj = db.get(m.Model, model_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Model not found")
    return obj


@router.get("/", response_model=List[ModelListItem])
def list_models(
    db: DbSessionDep,
    email: str = Query(..., min_length=1),
    project_id: int = Query(..., ge=1),
    limit: int = Query(100, ge=0, le=500),
    offset: int = Query(0, ge=0),
):
    # Verify ownership
    verify_project_ownership(db, project_id, email, m.Project, m.User)

    q = db.query(m.Model).filter(m.Model.project_id == project_id)
    q = q.order_by(m.Model.updated_at.desc(), m.Model.id.desc())
    if offset:
        q = q.offset(offset)
    if limit:
        q = q.limit(limit)
    # Returning full Model rows; response_model will serialize only id and name
    return q.all()




@router.get("/{model_id}", response_model=ModelRead)
def get_model(
    model_id: int,
    db: DbSessionDep,
    email: str = Query(..., min_length=1),
):
    obj = _get_or_404(db, model_id)
    verify_project_ownership(db, obj.project_id, email, m.Project, m.User)
    return obj




@router.post("/", response_model=ModelRead, status_code=201)
def create_model(
    payload: ModelCreate,
    db: DbSessionDep,
    email: str = Query(..., min_length=1),
):
    # Verify ownership of the project
    verify_project_ownership(db, payload.project_id, email, m.Project, m.User)

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




@router.patch("/{model_id}", response_model=ModelRead)
def update_model(
    model_id: int,
    payload: ModelUpdate,
    db: DbSessionDep,
    email: str = Query(..., min_length=1),
):
    obj = _get_or_404(db, model_id)
    verify_project_ownership(db, obj.project_id, email, m.Project, m.User)

    data = payload.model_dump(exclude_unset=True)
    apply_updates(obj, data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj




@router.delete("/{model_id}", status_code=204)
def delete_model(
    model_id: int,
    db: DbSessionDep,
    email: str = Query(..., min_length=1),
):
    obj = _get_or_404(db, model_id)
    verify_project_ownership(db, obj.project_id, email, m.Project, m.User)
    db.delete(obj)
    db.commit()
    return None


