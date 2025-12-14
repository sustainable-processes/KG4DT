from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException

from ...dependencies import DbSessionDep
from ...models.v2 import models as m
from ...schemas.v2.templates import TemplateCreate, TemplateRead, TemplateUpdate

router = APIRouter(prefix="/api/v2/templates", tags=["v2: templates"])


def _get_or_404(db: DbSessionDep, template_id: int) -> m.Template:
    obj = db.get(m.Template, template_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Template not found")
    return obj


@router.get("/", response_model=List[TemplateRead])
def list_templates(db: DbSessionDep):
    return db.query(m.Template).order_by(m.Template.id.desc()).all()


@router.get("/{template_id}", response_model=TemplateRead)
def get_template(template_id: int, db: DbSessionDep):
    return _get_or_404(db, template_id)


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


@router.patch("/{template_id}", response_model=TemplateRead)
def update_template(template_id: int, payload: TemplateUpdate, db: DbSessionDep):
    obj = _get_or_404(db, template_id)
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


@router.delete("/{template_id}", status_code=204)
def delete_template(template_id: int, db: DbSessionDep):
    obj = _get_or_404(db, template_id)
    db.delete(obj)
    db.commit()
    return None
