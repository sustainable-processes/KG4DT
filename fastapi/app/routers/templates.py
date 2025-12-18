from __future__ import annotations

from typing import List, Dict

from fastapi import APIRouter, HTTPException, Request

from ..dependencies import DbSessionDep
from .. import models as m
from ..schemas.templates import (
    TemplateCreate,
    TemplateRead,
    TemplateUpdate,
    AssemblyTemplatesResponse,
    GeneralTemplateItem,
    ReactorTile,
)
from sqlalchemy import func
from ..utils.graphdb_assembly_utils import list_context_templates_with_icons

router = APIRouter(prefix="/api/v1/assembly_templates", tags=["v1: assembly_templates"])


def _get_or_404(db: DbSessionDep, template_id: int) -> m.Template:
    obj = db.get(m.Template, template_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Template not found")
    return obj


@router.get("/", response_model=AssemblyTemplatesResponse)
def list_templates(db: DbSessionDep, request: Request):
    # Pull category, reactor info including icon
    rows = (
        db.query(m.Category.name, m.Reactor.id, m.Reactor.name, m.Reactor.icon_url)
        .join(m.Template, m.Template.category_id == m.Category.id)
        .join(m.Reactor, m.Template.reactor_id == m.Reactor.id)
        .order_by(m.Category.name.asc(), m.Reactor.name.asc())
        .all()
    )

    templates_list: List[ReactorTile] = []
    tutorials_list: List[ReactorTile] = []

    for category_name, reactor_id, reactor_name, icon_url in rows:
        item = ReactorTile(id=reactor_id, name=reactor_name, icon=icon_url)
        if str(category_name).strip().lower() == "templates":
            templates_list.append(item)
        elif str(category_name).strip().lower() == "tutorials":
            tutorials_list.append(item)

    # Build 'general' list from GraphDB context template names
    client = getattr(request.app.state, "graphdb", None)
    general_list: List[GeneralTemplateItem] = []
    if client is not None:
        name_icons = list_context_templates_with_icons(client)
        # Sorted by name for stable output
        general_list = [GeneralTemplateItem(name=n, icon=name_icons.get(n)) for n in sorted(name_icons.keys())]

    return {
        "Templates": templates_list,
        "Tutorials": tutorials_list,
        "General": general_list,
    }


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
