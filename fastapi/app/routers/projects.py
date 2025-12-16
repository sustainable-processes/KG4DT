from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from ..dependencies import DbSessionDep
from ..models import Project as ProjectModel
from ..models import User as UserModel
from ..schemas.projects import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(prefix="/api/v1/projects", tags=["v1: projects"])


def _get_project_or_404(db: DbSessionDep, project_id: int) -> ProjectModel:
    obj = db.get(ProjectModel, project_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Project not found")
    return obj


@router.get("/", response_model=List[ProjectRead])
def list_projects(
    db: DbSessionDep,
    user_id: Optional[int] = Query(None),
    limit: int = Query(100, ge=0, le=500),
    offset: int = Query(0, ge=0),
):
    q = db.query(ProjectModel)
    if user_id is not None:
        q = q.filter(ProjectModel.user_id == user_id)
    q = q.order_by(ProjectModel.updated_at.desc(), ProjectModel.created_at.desc())
    if offset:
        q = q.offset(offset)
    if limit:
        q = q.limit(limit)
    return q.all()


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: int, db: DbSessionDep):
    return _get_project_or_404(db, project_id)


@router.post("/", response_model=ProjectRead, status_code=201)
def create_project(payload: ProjectCreate, db: DbSessionDep):
    # Ensure user exists
    if not db.get(UserModel, payload.user_id):
        raise HTTPException(status_code=400, detail="Invalid user_id")
    # Enforce per-user unique name (case-insensitive) at API level (DB also enforces via index)
    exists = (
        db.query(ProjectModel)
        .filter(ProjectModel.user_id == payload.user_id)
        .filter(ProjectModel.name.ilike(payload.name))
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="Project name already exists for this user")

    obj = ProjectModel(user_id=payload.user_id, name=payload.name, content=payload.content or {})
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(project_id: int, payload: ProjectUpdate, db: DbSessionDep):
    obj = _get_project_or_404(db, project_id)
    data = payload.model_dump(exclude_unset=True)

    # If name or user_id changes, re-check uniqueness
    new_name = data.get("name", obj.name)
    new_user_id = data.get("user_id", obj.user_id)
    if new_name != obj.name or new_user_id != obj.user_id:
        exists = (
            db.query(ProjectModel)
            .filter(ProjectModel.user_id == new_user_id)
            .filter(ProjectModel.name.ilike(new_name))
            .filter(ProjectModel.id != obj.id)
            .first()
        )
        if exists:
            raise HTTPException(status_code=409, detail="Project name already exists for this user")

    for k, v in data.items():
        setattr(obj, k, v)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, db: DbSessionDep):
    obj = _get_project_or_404(db, project_id)
    db.delete(obj)
    db.commit()
    return None
