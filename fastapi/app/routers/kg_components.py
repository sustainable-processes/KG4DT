from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..utils.graphdb_assembly_utils import query_context_template
from ..utils.kg_translation import build_frontend_from_kg_context
from ..dependencies import DbSessionDep
from .. import models as m


router = APIRouter(prefix="/api/v1/kg_components", tags=["v1: kg_components"])
# Non-versioned duplicate under /api/kg_components
router_nv = APIRouter(prefix="/api/kg_components", tags=["kg_components"])


@router.get("/{component_id:int}")
def get_component_translated_by_id(component_id: int, db: DbSessionDep, request: Request):
    """Return translated frontend JSON for a KG context resolved by component ID.

    Steps:
    1) Look up `kg_components` by ID – 404 if not found.
    2) Use its name (with normalization rules) to fetch and translate the KG context.
       - If KG client is not configured → 503
       - If KG context cannot be found → 404
    """
    comp = db.get(m.KgComponent, component_id)
    if not comp:
        raise HTTPException(status_code=404, detail="KgComponent not found")

    return _translate_by_name(request, comp.name)


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


def _translate_by_name(request: Request, raw_name: str):
    """Shared implementation to translate a KG context by (possibly unnormalized) name.

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

    return build_frontend_from_kg_context(matched_key, data[matched_key])


@router.get("/{name}")
def get_translated_component(request: Request, name: str):
    """Return the translated frontend JSON for a KG context by name.

    Notes:
    - If the path contains "reactor" anywhere, it is normalized to "reactor vessel".
    - Case-insensitive match; underscores/spaces normalized for robustness.
    - No raw mode is supported; always returns the translated structure.
    """
    return _translate_by_name(request, name)


# -------- Non-versioned wrappers (/api/kg_components) --------

@router_nv.get("/{component_id:int}")
def get_component_translated_by_id_nv(component_id: int, db: DbSessionDep, request: Request):
    return get_component_translated_by_id(component_id, db, request)


@router_nv.get("/{name}")
def get_translated_component_nv(request: Request, name: str):
    return get_translated_component(request, name)
