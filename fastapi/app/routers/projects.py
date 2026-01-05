from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from ..dependencies import DbSessionDep
from ..models import Project as ProjectModel
from ..models import User as UserModel
from ..schemas.projects import ProjectCreate, ProjectRead, ProjectUpdate, ProjectListItem
from ..utils.db import apply_updates, validate_uniqueness, verify_project_ownership

router = APIRouter()
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



@router.get("/{project_id}", response_model=ProjectRead)
def get_project_by_id(
    project_id: int,
    db: DbSessionDep,
    email: str = Query(..., min_length=1),
):
    return verify_project_ownership(db, project_id, email, ProjectModel, UserModel)




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
    validate_uniqueness(
        db,
        ProjectModel,
        [ProjectModel.user_id == user.id, ProjectModel.name.ilike(payload.name)],
        error_message="Project name already exists for this user"
    )

    obj = ProjectModel(user_id=user.id, name=payload.name, content=payload.content or {})
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj




@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: int,
    db: DbSessionDep,
    payload: ProjectUpdate,
    email: str = Query(..., min_length=1),
):
    # Verify ownership
    obj = verify_project_ownership(db, project_id, email, ProjectModel, UserModel)

    data = payload.model_dump(exclude_unset=True)
    if not data:
        return obj

    # If renaming, check for uniqueness
    if "name" in data and data["name"] is not None:
        new_name = data["name"]
        if new_name.lower() != obj.name.lower():
            validate_uniqueness(
                db,
                ProjectModel,
                [ProjectModel.user_id == obj.user_id, ProjectModel.name.ilike(new_name)],
                exclude_id=obj.id,
                error_message="Project name already exists for this user"
            )

    # Generic update pattern
    apply_updates(obj, data)

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj




@router.delete("/{project_id}", status_code=204)
def delete_project_by_id(
    project_id: int,
    db: DbSessionDep,
    email: str = Query(..., min_length=1),
):
    obj = verify_project_ownership(db, project_id, email, ProjectModel, UserModel)

    db.delete(obj)
    db.commit()
    return None


download_router = APIRouter()


@download_router.get("/{project_id}")
def download_project_by_id(
    project_id: int,
    db: DbSessionDep,
    email: str = Query(..., min_length=1),
):
    """
    Download a project as a JSON file.
    Verifies ownership before allowing download.
    """
    # 1. Verify Ownership (Security Best Practice)
    obj = verify_project_ownership(db, project_id, email, ProjectModel, UserModel)

    # 2. Prepare Data (Translation Logic Placeholder)
    # We use the ProjectRead schema to ensure consistent serialization
    # In the future, this is where we would 'translate' or aggregate more data
    data = ProjectRead.model_validate(obj).model_dump()

    # 3. Secure & Consistent Serialization (Backend Best Practice)
    # jsonable_encoder ensures that datetime objects and other non-serializable 
    # types are converted to JSON-compatible formats correctly.
    json_data = jsonable_encoder(data)

    # 4. Forced Download (User Experience)
    # Setting Content-Disposition header to 'attachment' tells the browser 
    # to download the file instead of displaying it.
    filename = f"project_{obj.name}_{project_id}.json".replace(" ", "_")
    return JSONResponse(
        content=json_data,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


