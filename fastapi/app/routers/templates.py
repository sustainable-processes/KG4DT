from __future__ import annotations

from typing import List, Dict
import json
import logging

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
from ..utils.graphdb_assembly_utils import (
    list_context_template_names,
    query_context_template,
)

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
        db.query(m.Category.name, m.Reactor.id, m.Reactor.name, m.Reactor.icon)
        .join(m.Template, m.Template.category_id == m.Category.id)
        .join(m.Reactor, m.Template.reactor_id == m.Reactor.id)
        .order_by(m.Category.name.asc(), m.Reactor.name.asc())
        .all()
    )

    templates_list: List[ReactorTile] = []
    tutorials_list: List[ReactorTile] = []

    for category_name, reactor_id, reactor_name, icon in rows:
        item = ReactorTile(id=reactor_id, name=reactor_name, icon=icon)
        if str(category_name).strip().lower() == "templates":
            templates_list.append(item)
        elif str(category_name).strip().lower() == "tutorials":
            tutorials_list.append(item)

    # Build 'general' list from GraphDB context template names
    client = getattr(request.app.state, "graphdb", None)
    general_list: List[GeneralTemplateItem] = []
    if client is not None:
        # Print out all Knowledge Graph context template information
        try:
            kg_full = query_context_template(client)
            logging.getLogger(__name__).info(
                "Knowledge Graph context templates (full): %s",
                json.dumps(kg_full, indent=2, sort_keys=True),
            )
        except Exception as e:
            logging.getLogger(__name__).exception("Failed to fetch full KG context templates: %s", e)

        # Query names from KG, ensure they exist in kg_components table, and pull icons from DB
        try:
            names = list_context_template_names(client)
            logging.getLogger(__name__).info("KG context template names fetched: %d", len(names))

            if names:
                # Map existing KgComponent rows by lowercase name (case-insensitive match)
                lower_names = [n.lower() for n in names]
                existing_rows = (
                    db.query(m.KgComponent)
                    .filter(func.lower(m.KgComponent.name).in_(lower_names))
                    .all()
                )
                comp_by_lower: Dict[str, m.KgComponent] = {row.name.lower(): row for row in existing_rows}

                # Create any missing components with name only
                to_insert = [n for n in names if n.lower() not in comp_by_lower]
                for n in to_insert:
                    comp = m.KgComponent(name=n)
                    db.add(comp)
                    comp_by_lower[n.lower()] = comp
                if to_insert:
                    db.commit()
                    logging.getLogger(__name__).info(
                        "Inserted %d new kg_components from KG names.", len(to_insert)
                    )

                # Build response using DB ids and icons (None if not set)
                general_list = []
                for n in names:
                    comp = comp_by_lower.get(n.lower())
                    general_list.append(
                        GeneralTemplateItem(
                            id=(comp.id if comp else None),
                            name=n,
                            icon=(comp.icon if comp else None),
                        )
                    )
            else:
                general_list = []
        except Exception as e:
            logging.getLogger(__name__).exception("Failed to sync KG names with kg_components: %s", e)

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
