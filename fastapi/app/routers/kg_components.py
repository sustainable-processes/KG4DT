from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException, Request

from ..utils.graphdb_assembly_utils import query_context_template
from ..dependencies import DbSessionDep
from .. import models as m


router = APIRouter()


@router.get("/{component_id:int}")
def get_kg_component_by_id(component_id: int, db: DbSessionDep, request: Request):
    """Return frontend JSON for a KG context resolved by component ID.

    Steps:
    1) Look up `kg_components` by ID – 404 if not found.
    2) Use its name (with normalization rules) to fetch the KG context.
       - If KG client is not configured → 503
       - If KG context cannot be found → 404
    """
    comp = db.get(m.KgComponent, component_id)
    if not comp:
        raise HTTPException(status_code=404, detail="KgComponent not found")

    res = _get_kg_component_by_name(request, comp.name)
    if isinstance(res, dict):
        res["id"] = comp.id
        res["icon"] = str(comp.icon).lower() if comp.icon else None
        res["node_type"] = str(comp.node_type).lower() if comp.node_type else None
        res["type"] = str(comp.type).lower() if comp.type else None
    return res


def _normalize_name_for_match(raw: str) -> str:
    """Normalize incoming context name for matching.

    - If contains "reactor" (case-insensitive), force to "reactor vessel".
    - Lowercase and replace underscores with spaces for robust comparison.
    """
    if not isinstance(raw, str):
        return ""
    name = raw.strip()
    if "reactor" in name.lower():
        name = "reactor vessel"
    return name.lower().replace("_", " ")


def _get_kg_component_by_name(request: Request, raw_name: str):
    """Shared implementation to fetch a KG context by (possibly unnormalized) name.

    Applies the same normalization and matching as the name-based endpoint.
    """
    client = getattr(request.app.state, "graphdb", None)
    if client is None:
        raise HTTPException(status_code=503, detail="Knowledge Graph client is not configured")

    data = query_context_template(client)

    target_norm = _normalize_name_for_match(raw_name)

    matched_key = None
    for k in data.keys():
        k_norm = k.lower().replace("_", " ")
        if k_norm == target_norm:
            matched_key = k
            break

    if matched_key is None:
        lowered = raw_name.strip().lower()
        matched_key = next((k for k in data.keys() if k.lower() == lowered), None)

    if matched_key is None:
        raise HTTPException(status_code=404, detail="Context template not found in Knowledge Graph")

    # Convert everything to small cap as requested
    def lowercase_recursive(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {str(k).lower(): lowercase_recursive(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [lowercase_recursive(i) for i in obj]
        elif isinstance(obj, str):
            return obj.lower()
        return obj

    # Flatten the detail directly into the response and add the name
    res = {
        "name": matched_key,
    }
    res.update(data[matched_key])

    res = lowercase_recursive(res)
    if isinstance(res, dict) and "name" in res:
        res["label"] = str(res["name"]).replace("_", " ").capitalize()
    return res


@router.get("/{name}")
def get_kg_component_by_name(request: Request, name: str, db: DbSessionDep):
    """Return the frontend JSON for a KG context by name.

    Notes:
    - If the path contains "reactor" anywhere, it is normalized to "reactor vessel".
    - Case-insensitive match; underscores/spaces normalized for robustness.
    - No raw mode is supported; always returns the mapped structure.
    """
    res = _get_kg_component_by_name(request, name)
    if isinstance(res, dict):
        # Try to find corresponding metadata in DB
        target_norm = _normalize_name_for_match(name)
        comp = db.query(m.KgComponent).filter(m.KgComponent.name.ilike(target_norm)).first()
        if not comp:
             # Fallback to case-insensitive exact name match if normalization fails
             comp = db.query(m.KgComponent).filter(m.KgComponent.name.ilike(name.strip())).first()

        if comp:
            res["id"] = comp.id
            res["icon"] = str(comp.icon).lower() if comp.icon else None
            res["node_type"] = str(comp.node_type).lower() if comp.node_type else None
            res["type"] = str(comp.type).lower() if comp.type else None
        else:
            res["id"] = None
            res["icon"] = None
            res["node_type"] = None
            res["type"] = None
    return res


