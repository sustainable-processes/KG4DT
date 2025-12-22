from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException

from ..dependencies import DbSessionDep
from .. import models as m
from ..schemas.experiment_data import (
    ExperimentDataCreate,
    ExperimentDataRead,
    ExperimentDataUpdate,
)
from ..utils.db import apply_updates

router = APIRouter()


def _get_or_404(db: DbSessionDep, exp_id: int) -> m.ExperimentData:
    obj = db.get(m.ExperimentData, exp_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Experiment data not found")
    return obj


@router.get("/", response_model=List[ExperimentDataRead])
def list_experiment_data(db: DbSessionDep):
    return db.query(m.ExperimentData).order_by(m.ExperimentData.id.desc()).all()




@router.get("/{exp_id}", response_model=ExperimentDataRead)
def get_experiment(exp_id: int, db: DbSessionDep):
    return _get_or_404(db, exp_id)




@router.post("/", response_model=ExperimentDataRead, status_code=201)
def create_experiment(payload: ExperimentDataCreate, db: DbSessionDep):
    # Ensure project exists
    if not db.get(m.Project, payload.project_id):
        raise HTTPException(status_code=400, detail="Invalid project_id")
    obj = m.ExperimentData(project_id=payload.project_id, data=payload.data or {})
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj




@router.patch("/{exp_id}", response_model=ExperimentDataRead)
def update_experiment(exp_id: int, payload: ExperimentDataUpdate, db: DbSessionDep):
    obj = _get_or_404(db, exp_id)
    data = payload.model_dump(exclude_unset=True)
    apply_updates(obj, data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj




@router.delete("/{exp_id}", status_code=204)
def delete_experiment(exp_id: int, db: DbSessionDep):
    obj = _get_or_404(db, exp_id)
    db.delete(obj)
    db.commit()
    return None


