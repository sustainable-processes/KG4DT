from __future__ import annotations

from typing import Any, Dict, Iterable, List

from fastapi import APIRouter, HTTPException, Query, Request

from ..schemas.types import JsonDict
from ..utils.graphdb_assembly_utils import query_context_template
from ..utils.kg_translation import build_frontend_from_kg_context


router = APIRouter(prefix="/api/v1", tags=["v1: translate"])


def _unique_preserve(seq: Iterable[Any]) -> List[Any]:
    seen = set()
    out: List[Any] = []
    for x in seq:
        if x is None:
            continue
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _flatten_phases(phases: Any) -> List[Any]:
    """Flatten phases to a simple list of species names.

    Accepts either a dict like {"phase 1": ["a", "b"], ...}, or a list,
    or any other JSON structure. Non-list/str items are ignored.
    """
    if phases is None:
        return []
    if isinstance(phases, list):
        return [x for x in phases if isinstance(x, (str, int, float))]
    if isinstance(phases, dict):
        flat: List[Any] = []
        for v in phases.values():
            if isinstance(v, list):
                flat.extend([x for x in v if isinstance(x, (str, int, float))])
            elif isinstance(v, (str, int, float)):
                flat.append(v)
        return flat
    return []


def build_basic_context_from_frontend(payload: JsonDict) -> Dict[str, Any]:
    """Build the `context.basic` section from a frontend JSON payload.

    Rules implemented:
    - basic.spc from top-level chemistry.species[].name (unique, order-preserving)
    - basic.rxn from chemistry.reactions[].elementary (flattened strings, unique, order-preserving)
    - basic.stm/sld/gas from entries under `input` based on their `type`:
      - key: the input name (dictionary key)
      - value: { spc: flattened phases values; rxn: from that input's chemistry.reaction (if present/non-empty) }
    """
    chemistry = payload.get("chemistry") or {}
    species = chemistry.get("species") or []
    reactions = chemistry.get("reactions") or []

    # basic.spc
    basic_spc = _unique_preserve(
        [s.get("name") for s in species if isinstance(s, dict) and s.get("name")]
    )

    # basic.rxn
    rxn_flat: List[str] = []
    for r in reactions:
        if not isinstance(r, dict):
            continue
        elem = r.get("elementary")
        if isinstance(elem, list):
            rxn_flat.extend([e for e in elem if isinstance(e, str)])
        elif isinstance(elem, str):
            rxn_flat.append(elem)
    basic_rxn = _unique_preserve(rxn_flat)

    # Inputs
    inputs: Dict[str, Any] = payload.get("input") or {}
    stm: Dict[str, Any] = {}
    sld: Dict[str, Any] = {}
    gas: Dict[str, Any] = {}

    for name, item in inputs.items():
        if not isinstance(item, dict):
            continue
        typ = (item.get("type") or "").lower()
        phases = _flatten_phases(item.get("phases"))
        rxn_local = []
        chem_local = item.get("chemistry") if isinstance(item.get("chemistry"), dict) else {}
        if isinstance(chem_local.get("reaction"), list):
            rxn_local = [x for x in chem_local.get("reaction") if isinstance(x, str)]

        entry: Dict[str, Any] = {"spc": _unique_preserve(phases)}
        if rxn_local:
            entry["rxn"] = _unique_preserve(rxn_local)

        if typ == "steam":
            stm[name] = entry
        elif typ == "solid":
            sld[name] = entry
        elif typ == "gas":
            gas[name] = entry
        else:
            # Unknown types are ignored for `basic`
            continue

    basic: Dict[str, Any] = {
        "spc": basic_spc,
        "rxn": basic_rxn,
    }
    if stm:
        basic["stm"] = stm
    if sld:
        basic["sld"] = sld
    if gas:
        basic["gas"] = gas

    return basic


@router.post("/translate_frontend_json")
def translate_frontend_json(payload: JsonDict) -> Dict[str, Any]:
    """Translate frontend JSON into backend context structure (basic only).

    Returns:
      {
        "context": {
          "type": "dynamic",
          "basic": { ... }
        }
      }
    """
    basic = build_basic_context_from_frontend(payload)
    return {"context": {"type": "dynamic", "basic": basic}}


# ---------------------- KG -> Frontend translation ----------------------
"""Reusable KG→Frontend translator is implemented in fastapi.app.utils.kg_translation.
This router keeps only frontend→backend translation endpoint. The KG→Frontend
endpoint is now exposed under /api/v1/kg_components/{name}."""
