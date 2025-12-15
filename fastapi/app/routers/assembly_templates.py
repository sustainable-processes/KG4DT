from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

from fastapi import APIRouter

from ..dependencies import DbSessionDep
from ..models.template import Template
from ..models.reactor import Reactor


router = APIRouter(prefix="/models", tags=["assembly_templates"])  # under /models per request


def _safe_iso(dt) -> Optional[str]:
    try:
        return dt.isoformat() if dt is not None else None
    except Exception:
        return None


@router.get("/assembly_templates")
def get_assembly_templates(db: DbSessionDep) -> Dict[str, List[Dict[str, Any]]]:
    """Return templates grouped by category with embedded reactor data.

    Response shape:
      {
        "<Category>": [
          {
            "name": <reactor.name>,
            "icon": <reactor.icon>,
            "created_date": <ISO string>,
            "number_of_input": <int>,
            "number_of_utility_input": <int>,
            "chemistry": <dict>,
            "phenomenon": <dict>,
            "input": <dict>,
            "utility": <dict>,
            "reactor": <dict>
          },
          ...
        ],
        ...
      }

    Notes:
    - The input/utility/reactor sections are taken from Reactor.json_data if present.
    - If a Template references a missing Reactor, it is skipped.
    """
    # Fetch all templates and their reactors in two queries for efficiency
    templates: List[Template] = db.query(Template).all()
    reactor_ids = sorted({t.reactor_id for t in templates if t.reactor_id is not None})

    reactors: Dict[int, Reactor] = {}
    if reactor_ids:
        for r in db.query(Reactor).filter(Reactor.id.in_(reactor_ids)).all():
            reactors[r.id] = r

    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for t in templates:
        r = reactors.get(t.reactor_id)
        if not r:
            # Skip broken FK to avoid null-heavy objects
            continue

        jd = r.json_data or {}
        item: Dict[str, Any] = {
            "name": r.name,
            "icon": r.icon,
            "created_date": _safe_iso(r.created_date),
            "number_of_input": r.number_of_input,
            "number_of_utility_input": r.number_of_utility_input,
            "chemistry": r.chemistry or {},
            "kinetics": r.kinetics or {},
            # Sections from json_data when provided
            "input": jd.get("input", {} if isinstance(jd, dict) else {}),
            "utility": jd.get("utility", {} if isinstance(jd, dict) else {}),
            "reactor": jd.get("reactor", {} if isinstance(jd, dict) else {}),
        }

        grouped[t.category].append(item)

    # Convert defaultdict to plain dict for JSON response
    return {k: v for k, v in grouped.items()}
