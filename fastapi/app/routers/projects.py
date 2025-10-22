from __future__ import annotations

from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException, Query

from ..dependencies import DbSessionDep
from ..models.project import Project
from ..schemas.project import ProjectCreate, ProjectUpdate, ProjectRead

router = APIRouter(prefix="/models/projects", tags=["models", "projects"])


@router.get("/", response_model=List[ProjectRead])
def list_projects(db: DbSessionDep, limit: int = Query(100, ge=0, le=500), offset: int = Query(0, ge=0), user_id: Optional[int] = Query(None)):
    q = db.query(Project)
    if user_id is not None:
        q = q.filter(Project.user_id == user_id)
    q = q.order_by(Project.last_update.desc(), Project.datetime.desc(), Project.id.desc())
    if offset:
        q = q.offset(offset)
    if limit:
        q = q.limit(limit)
    return q.all()


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: int, db: DbSessionDep):
    obj = db.get(Project, project_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Project not found")
    return obj


@router.post("/", response_model=ProjectRead, status_code=201)
def create_project(payload: ProjectCreate, db: DbSessionDep):
    obj = Project(
        name=payload.name,
        user_id=payload.user_id,
        model=payload.model,
        content=payload.content,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(project_id: int, payload: ProjectUpdate, db: DbSessionDep):
    obj: Optional[Project] = db.get(Project, project_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Project not found")

    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(obj, k, v)

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, db: DbSessionDep):
    obj: Optional[Project] = db.get(Project, project_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(obj)
    db.commit()
    return None
