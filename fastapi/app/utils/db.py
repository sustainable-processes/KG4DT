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
