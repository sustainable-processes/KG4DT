from __future__ import annotations

import csv
import io
from typing import List

from fastapi import APIRouter, HTTPException, Query, File, UploadFile, Form

from ..dependencies import DbSessionDep
from .. import models as m
from ..schemas.experiment_data import (
    ExperimentDataCreate,
    ExperimentDataRead,
    ExperimentDataUpdate,
)
from ..utils.db import apply_updates, verify_project_ownership

router = APIRouter()


def _get_or_404(db: DbSessionDep, exp_id: int) -> m.ExperimentData:
    obj = db.get(m.ExperimentData, exp_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Experiment data not found")
    return obj


@router.get("/", response_model=List[ExperimentDataRead])
def list_experiment_data(
    db: DbSessionDep,
    email: str = Query(..., min_length=1),
    project_id: int = Query(..., ge=1),
):
    verify_project_ownership(db, project_id, email, m.Project, m.User)
    return (
        db.query(m.ExperimentData)
        .filter(m.ExperimentData.project_id == project_id)
        .order_by(m.ExperimentData.id.desc())
        .all()
    )




@router.get("/{exp_id}", response_model=ExperimentDataRead)
def get_experiment(
    exp_id: int,
    db: DbSessionDep,
    email: str = Query(..., min_length=1),
):
    obj = _get_or_404(db, exp_id)
    verify_project_ownership(db, obj.project_id, email, m.Project, m.User)
    return obj




@router.post("/", response_model=ExperimentDataRead, status_code=201)
def create_experiment(
    payload: ExperimentDataCreate,
    db: DbSessionDep,
    email: str = Query(..., min_length=1),
):
    # Verify ownership of the project
    verify_project_ownership(db, payload.project_id, email, m.Project, m.User)

    # Verify that the model exists and belongs to the same project
    model = db.get(m.Model, payload.model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    if model.project_id != payload.project_id:
        raise HTTPException(
            status_code=400,
            detail="Model does not belong to the specified project",
        )

    obj = m.ExperimentData(
        project_id=payload.project_id,
        model_id=payload.model_id,
        data=payload.data or {},
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/upload", response_model=ExperimentDataRead, status_code=201)
async def upload_experiment_data(
    db: DbSessionDep,
    project_id: int = Form(...),
    model_id: int = Form(...),
    file: UploadFile = File(...),
    email: str = Query(..., min_length=1),
):
    """Upload a CSV file and save its content as ExperimentData.

    The CSV content will be parsed and stored in the 'data' field as a list of objects.
    """
    # Verify ownership of the project
    verify_project_ownership(db, project_id, email, m.Project, m.User)

    # Verify that the model exists and belongs to the same project
    model = db.get(m.Model, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    if model.project_id != project_id:
        raise HTTPException(
            status_code=400,
            detail="Model does not belong to the specified project",
        )

    # Read and parse CSV
    try:
        contents = await file.read()
        decoded = contents.decode("utf-8")
        # Use io.StringIO to make the string behave like a file for csv.DictReader
        reader = csv.DictReader(io.StringIO(decoded))
        data_list = []
        for row in reader:
            # Optionally convert numeric values
            processed_row = {}
            for k, v in row.items():
                if v is not None:
                    v_str = str(v).strip()
                    try:
                        # Try to convert to float/int if possible
                        if "." in v_str:
                            processed_row[k] = float(v_str)
                        else:
                            processed_row[k] = int(v_str)
                    except ValueError:
                        processed_row[k] = v_str
                else:
                    processed_row[k] = v
            data_list.append(processed_row)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {str(e)}")

    if not data_list:
        raise HTTPException(status_code=400, detail="CSV file is empty or invalid")

    obj = m.ExperimentData(
        project_id=project_id,
        model_id=model_id,
        data=data_list,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj




@router.patch("/{exp_id}", response_model=ExperimentDataRead)
def update_experiment(
    exp_id: int,
    payload: ExperimentDataUpdate,
    db: DbSessionDep,
    email: str = Query(..., min_length=1),
):
    obj = _get_or_404(db, exp_id)
    verify_project_ownership(db, obj.project_id, email, m.Project, m.User)

    data = payload.model_dump(exclude_unset=True)

    # Validate model_id if provided
    new_model_id = data.get("model_id")
    if new_model_id is not None:
        model = db.get(m.Model, new_model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        # Ensure it belongs to the same project (ExperimentData project_id is immutable here for simplicity)
        if model.project_id != obj.project_id:
            raise HTTPException(
                status_code=400,
                detail="Model does not belong to the same project as the experiment data",
            )

    apply_updates(obj, data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj




@router.delete("/{exp_id}", status_code=204)
def delete_experiment(
    exp_id: int,
    db: DbSessionDep,
    email: str = Query(..., min_length=1),
):
    obj = _get_or_404(db, exp_id)
    verify_project_ownership(db, obj.project_id, email, m.Project, m.User)
    db.delete(obj)
    db.commit()
    return None


