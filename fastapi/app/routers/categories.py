from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException

from ..dependencies import DbSessionDep
from .. import models as m
from ..schemas.categories import CategoryCreate, CategoryRead, CategoryUpdate
from ..utils.db import apply_updates, validate_uniqueness

router = APIRouter()


def _get_or_404(db: DbSessionDep, category_id: int) -> m.Category:
    obj = db.get(m.Category, category_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Category not found")
    return obj


@router.get("/", response_model=List[CategoryRead])
def list_categories(db: DbSessionDep):
    return db.query(m.Category).order_by(m.Category.name.asc()).all()


@router.get("/{category_id}", response_model=CategoryRead)
def get_category(category_id: int, db: DbSessionDep):
    return _get_or_404(db, category_id)


@router.post("/", response_model=CategoryRead, status_code=201)
def create_category(payload: CategoryCreate, db: DbSessionDep):
    validate_uniqueness(db, m.Category, [m.Category.name.ilike(payload.name)], error_message="Category name already exists")
    obj = m.Category(name=payload.name)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{category_id}", response_model=CategoryRead)
def update_category(category_id: int, payload: CategoryUpdate, db: DbSessionDep):
    obj = _get_or_404(db, category_id)
    data = payload.model_dump(exclude_unset=True)

    if "name" in data and data["name"] != obj.name:
        validate_uniqueness(db, m.Category, [m.Category.name.ilike(data["name"])], exclude_id=obj.id, error_message="Category name already exists")

    apply_updates(obj, data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{category_id}", status_code=204)
def delete_category(category_id: int, db: DbSessionDep):
    obj = _get_or_404(db, category_id)
    db.delete(obj)
    db.commit()
    return None
