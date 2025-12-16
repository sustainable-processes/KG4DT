from __future__ import annotations

from typing import List, Dict

from fastapi import APIRouter, HTTPException

from ..dependencies import DbSessionDep
from .. import models as m
from ..schemas.templates import TemplateCreate, TemplateRead, TemplateUpdate
from ..schemas.reactors import ReactorBrief
from sqlalchemy import func

router = APIRouter(prefix="/api/v1/assembly_templates", tags=["v1: assembly_templates"])


def _get_or_404(db: DbSessionDep, template_id: int) -> m.Template:
    obj = db.get(m.Template, template_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Template not found")
    return obj


@router.get("/", response_model=List[Dict[str, List[ReactorBrief]]])
def list_templates(db: DbSessionDep):
    # Group templates by category name and list their reactors (id, name)
    rows = (
        db.query(m.Category.name, m.Reactor.id, m.Reactor.name)
        .join(m.Template, m.Template.category_id == m.Category.id)
        .join(m.Reactor, m.Template.reactor_id == m.Reactor.id)
        .order_by(m.Category.name.asc(), m.Reactor.name.asc())
        .all()
    )

    grouped: dict[str, list[dict[str, object]]] = {}
    for category_name, reactor_id, reactor_name in rows:
        grouped.setdefault(category_name, []).append({"id": reactor_id, "name": reactor_name})

    # Convert mapping to requested list-of-single-key-objects format
    return [{category: reactors} for category, reactors in grouped.items()]


def _get_by_category_and_reactor_or_404(db: DbSessionDep, category_name: str, reactor_id: int) -> m.Template:
    category = (
        db.query(m.Category)
        .filter(func.lower(m.Category.name) == func.lower(category_name))
        .first()
    )
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    obj = (
        db.query(m.Template)
        .filter(m.Template.category_id == category.id, m.Template.reactor_id == reactor_id)
        .first()
    )
    if not obj:
        raise HTTPException(status_code=404, detail="Template not found for provided category/reactor")
    return obj


@router.post("/", response_model=TemplateRead, status_code=201)
def create_template(payload: TemplateCreate, db: DbSessionDep):
    # Unique per (category_id, reactor_id)
    exists = (
        db.query(m.Template)
        .filter(m.Template.category_id == payload.category_id, m.Template.reactor_id == payload.reactor_id)
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="Template already exists for this category/reactor")
    obj = m.Template(category_id=payload.category_id, reactor_id=payload.reactor_id)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{category_name}/{reactor_id}", response_model=TemplateRead)
def update_template(category_name: str, reactor_id: int, payload: TemplateUpdate, db: DbSessionDep):
    obj = _get_by_category_and_reactor_or_404(db, category_name, reactor_id)
    data = payload.model_dump(exclude_unset=True)
    if "category_id" in data or "reactor_id" in data:
        cat_id = data.get("category_id", obj.category_id)
        reac_id = data.get("reactor_id", obj.reactor_id)
        exists = (
            db.query(m.Template)
            .filter(m.Template.category_id == cat_id, m.Template.reactor_id == reac_id, m.Template.id != obj.id)
            .first()
        )
        if exists:
            raise HTTPException(status_code=409, detail="Template already exists for this category/reactor")
    for k, v in data.items():
        setattr(obj, k, v)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{category_name}/{reactor_id}", status_code=204)
def delete_template(category_name: str, reactor_id: int, db: DbSessionDep):
    obj = _get_by_category_and_reactor_or_404(db, category_name, reactor_id)
    db.delete(obj)
    db.commit()
    return None
