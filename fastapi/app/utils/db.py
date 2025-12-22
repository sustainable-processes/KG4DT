from __future__ import annotations

from typing import Any, Dict, Type, Iterable
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import Column, inspect

def apply_updates(obj: Any, data: Dict[str, Any]) -> None:
    """
    Generic update pattern: apply key-value pairs from data to obj.
    Only updates attributes that already exist on the object.
    """
    for k, v in data.items():
        if hasattr(obj, k):
            setattr(obj, k, v)

def validate_uniqueness(
    db: Session,
    model: Type[Any],
    constraints: Iterable[Any],
    exclude_id: Any = None,
    id_field: str = "id",
    error_message: str = "Resource already exists"
) -> None:
    """
    Validates uniqueness of a record given a set of filters (constraints).
    If a conflict is found, raises an HTTPException with status code 409.
    """
    query = db.query(model).filter(*constraints)
    if exclude_id is not None:
        query = query.filter(getattr(model, id_field) != exclude_id)
    
    if query.first():
        raise HTTPException(status_code=409, detail=error_message)

def verify_project_ownership(
    db: Session,
    project_id: int,
    email: str,
    Project: Type[Any],
    User: Type[Any],
) -> Any:
    """
    Verifies that a user with the given email owns the project with project_id.
    Raises 403 if user not found or doesn't own the project.
    Raises 404 if project not found.
    Returns the project object.
    """
    email_lower = email.strip().lower()
    user = db.query(User).filter(User.email == email_lower).first()
    if not user:
        raise HTTPException(status_code=403, detail="Not authorized to access this project")

    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this project")

    return project
