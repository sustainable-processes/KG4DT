from __future__ import annotations

from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException, Query

from ..dependencies import DbSessionDep
from ..models.project import Project
from ..schemas.project import ProjectCreate, ProjectUpdate, ProjectRead

router = APIRouter(prefix="/models/projects", tags=["projects"])


def _get_project_by_name_or_error(db: DbSessionDep, name: str) -> Project:
    """Fetch a single project by name, raising HTTP errors if not found or duplicate.

    - 404 if no project with the given name exists
    - 409 if multiple projects share the same name (ambiguous)
    """
    matches: list[Project] = (
        db.query(Project).filter(Project.name == name).order_by(Project.last_update.desc(), Project.id.desc()).all()
    )
    if not matches:
        raise HTTPException(status_code=404, detail="Project not found")
    if len(matches) > 1:
        raise HTTPException(status_code=409, detail="Multiple projects found with the same name; operation is ambiguous")
    return matches[0]


@router.get("/", response_model=List[str])
def list_projects(
    db: DbSessionDep,
    limit: int = Query(100, ge=0, le=500),
    offset: int = Query(0, ge=0),
    user_id: Optional[int] = Query(None),
):
    q = db.query(Project)
    if user_id is not None:
        q = q.filter(Project.user_id == user_id)
    q = q.order_by(Project.last_update.desc(), Project.datetime.desc(), Project.id.desc())
    if offset:
        q = q.offset(offset)
    if limit:
        q = q.limit(limit)
    # Return only the list of project names
    rows = q.with_entities(Project.name).all()
    return [r[0] for r in rows]


@router.get("/{project_name}", response_model=ProjectRead)
def get_project(project_name: str, db: DbSessionDep):
    return _get_project_by_name_or_error(db, project_name)


@router.post("/", response_model=ProjectRead, status_code=201)
def create_project(payload: ProjectCreate, db: DbSessionDep):
    # Enforce unique project names to ensure name-based lookups are unambiguous
    existing = db.query(Project).filter(Project.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Project name already exists")
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


@router.patch("/{project_name}", response_model=ProjectRead)
def update_project(project_name: str, payload: ProjectUpdate, db: DbSessionDep):
    obj: Project = _get_project_by_name_or_error(db, project_name)

    data = payload.model_dump(exclude_unset=True)

    # If renaming, ensure the new name is not taken by another project
    new_name = data.get("name")
    if new_name and new_name != obj.name:
        exists = db.query(Project).filter(Project.name == new_name).first()
        if exists:
            raise HTTPException(status_code=409, detail="Target project name already exists")

    for k, v in data.items():
        setattr(obj, k, v)

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{project_name}", status_code=204)
def delete_project(project_name: str, db: DbSessionDep):
    obj: Project = _get_project_by_name_or_error(db, project_name)
    db.delete(obj)
    db.commit()
    return None
