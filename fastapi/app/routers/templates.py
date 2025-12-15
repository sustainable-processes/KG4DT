from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from ..dependencies import DbSessionDep
from ..models.template import Template
from ..schemas.template import TemplateCreate, TemplateUpdate, TemplateRead


router = APIRouter(prefix="/models/templates", tags=["templates"])


@router.get("/", response_model=List[TemplateRead])
def list_templates(db: DbSessionDep, limit: int = Query(100, ge=0, le=500), offset: int = Query(0, ge=0)):
    q = db.query(Template).order_by(Template.id.desc()).offset(offset)
    if limit:
        q = q.limit(limit)
    return q.all()


@router.get("/{template_id}", response_model=TemplateRead)
def get_template(template_id: int, db: DbSessionDep):
    obj = db.get(Template, template_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Template not found")
    return obj


@router.post("/", response_model=TemplateRead, status_code=201)
def create_template(payload: TemplateCreate, db: DbSessionDep):
    obj = Template(category=payload.category, reactor_id=payload.reactor_id)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{template_id}", response_model=TemplateRead)
def update_template(template_id: int, payload: TemplateUpdate, db: DbSessionDep):
    obj: Optional[Template] = db.get(Template, template_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Template not found")

    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(obj, k, v)

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{template_id}", status_code=204)
def delete_template(template_id: int, db: DbSessionDep):
    obj: Optional[Template] = db.get(Template, template_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(obj)
    db.commit()
    return None
