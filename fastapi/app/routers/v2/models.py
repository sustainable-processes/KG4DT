from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException

from ...dependencies import DbSessionDep
from ...models.v2 import models as m
from ...schemas.v2.models import ModelCreate, ModelRead, ModelUpdate

router = APIRouter(prefix="/api/v2/models", tags=["v2: models"])


def _get_or_404(db: DbSessionDep, model_id: int) -> m.Model:
    obj = db.get(m.Model, model_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Model not found")
    return obj


@router.get("/", response_model=List[ModelRead])
def list_models(db: DbSessionDep):
    return db.query(m.Model).order_by(m.Model.updated_at.desc(), m.Model.id.desc()).all()


@router.get("/{model_id}", response_model=ModelRead)
def get_model(model_id: int, db: DbSessionDep):
    return _get_or_404(db, model_id)


@router.post("/", response_model=ModelRead, status_code=201)
def create_model(payload: ModelCreate, db: DbSessionDep):
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


@router.delete("/{model_id}", status_code=204)
def delete_model(model_id: int, db: DbSessionDep):
    obj = _get_or_404(db, model_id)
    db.delete(obj)
    db.commit()
    return None
