from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, Query

from ..dependencies import DbSessionDep
from ..models import Project as ProjectModel
from ..models import User as UserModel
from ..schemas.projects import ProjectCreate, ProjectRead, ProjectUpdate, ProjectListItem

router = APIRouter(prefix="/api/v1/projects", tags=["v1: projects"])
# Non-versioned duplicate under /api/projects
router_nv = APIRouter(prefix="/api/projects", tags=["projects"])
"""Project endpoints (ID-based for get/patch/delete)."""


@router.get("/", response_model=List[ProjectListItem])
def list_projects(
    db: DbSessionDep,
    email: str = Query(..., min_length=1),
    limit: int = Query(100, ge=0, le=500),
    offset: int = Query(0, ge=0),
):
    # Resolve email to user_id; create user if not exists
    email_lower = email.strip().lower()
    user = db.query(UserModel).filter(UserModel.email == email_lower).first()
    if not user:
        user = UserModel(username=email_lower, email=email_lower)
        db.add(user)
        db.commit()
        db.refresh(user)

    # Fetch projects belonging to the user (response model will expose only id and name)
    q = db.query(ProjectModel).filter(ProjectModel.user_id == user.id)
    q = q.order_by(ProjectModel.updated_at.desc(), ProjectModel.created_at.desc())
    if offset:
        q = q.offset(offset)
    if limit:
        q = q.limit(limit)
    projects = q.all()
    return projects


@router_nv.get("/", response_model=List[ProjectListItem])
def list_projects_nv(
    db: DbSessionDep,
    email: str = Query(..., min_length=1),
    limit: int = Query(100, ge=0, le=500),
    offset: int = Query(0, ge=0),
):
    return list_projects(db=db, email=email, limit=limit, offset=offset)

@router.get("/{project_id}", response_model=ProjectRead)
def get_project_by_id(
    project_id: int,
    db: DbSessionDep,
):
    project = db.get(ProjectModel, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router_nv.get("/{project_id}", response_model=ProjectRead)
def get_project_by_id_nv(
    project_id: int,
    db: DbSessionDep,
):
    return get_project_by_id(project_id, db)


@router.post("/", response_model=ProjectRead, status_code=201)
def create_project(payload: ProjectCreate, db: DbSessionDep):
    # Resolve user via email only (creates if missing)
    email_lower = payload.email.strip().lower()
    user = db.query(UserModel).filter(UserModel.email == email_lower).first()
    if not user:
        user = UserModel(username=email_lower, email=email_lower)
        db.add(user)
        db.commit()
        db.refresh(user)

    # Enforce per-user unique name (case-insensitive) at API level
    exists = (
        db.query(ProjectModel)
        .filter(ProjectModel.user_id == user.id)
        .filter(ProjectModel.name.ilike(payload.name))
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="Project name already exists for this user")

    obj = ProjectModel(user_id=user.id, name=payload.name, content=payload.content or {})
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router_nv.post("/", response_model=ProjectRead, status_code=201)
def create_project_nv(payload: ProjectCreate, db: DbSessionDep):
    return create_project(payload, db)


@router.patch("/{project_id}", response_model=ProjectRead)
def rename_project(
    project_id: int,
    db: DbSessionDep,
    payload: ProjectUpdate | None = None,
):
    # Find existing project by id
    obj = db.get(ProjectModel, project_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Project not found")

    # Only allow renaming: take only 'name' from payload
    if payload is None:
        raise HTTPException(status_code=400, detail="Request body required with new name")
    data = payload.model_dump(exclude_unset=True)
    if not data or "name" not in data:
        raise HTTPException(status_code=400, detail="Only 'name' is allowed and required for rename")

    new_name = data.get("name")

    # If name is the same (case-insensitive), just return current object
    if new_name.lower() == obj.name.lower():
        return obj

    # Enforce per-user unique name (case-insensitive)
    exists = (
        db.query(ProjectModel)
        .filter(ProjectModel.user_id == obj.user_id)
        .filter(ProjectModel.name.ilike(new_name))
        .filter(ProjectModel.id != obj.id)
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="Project name already exists for this user")

    obj.name = new_name
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router_nv.patch("/{project_id}", response_model=ProjectRead)
def rename_project_nv(
    project_id: int,
    db: DbSessionDep,
    payload: ProjectUpdate | None = None,
):
    return rename_project(project_id, db, payload)


@router.delete("/{project_id}", status_code=204)
def delete_project_by_id(
    project_id: int,
    db: DbSessionDep,
):
    obj = db.get(ProjectModel, project_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(obj)
    db.commit()
    return None


@router_nv.delete("/{project_id}", status_code=204)
def delete_project_by_id_nv(
    project_id: int,
    db: DbSessionDep,
):
    return delete_project_by_id(project_id, db)
