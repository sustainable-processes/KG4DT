from __future__ import annotations

from typing import Any, Dict, Iterable, List
from ..schemas.translation import FrontendPayload, BackendContextBasic, BackendContextDesc, BackendContext


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
    """Flatten phases to a simple list of species names."""
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


def build_basic_context(payload: FrontendPayload) -> BackendContextBasic:
    """Build the `context.basic` section from a frontend payload."""
    chemistry = payload.chemistry or {}
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
    inputs: Dict[str, Any] = payload.input or {}
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

        if typ == "stream":
            stm[name] = entry
        elif typ == "solid":
            sld[name] = entry
        elif typ == "gas":
            gas[name] = entry

    return BackendContextBasic(
        spc=basic_spc,
        rxn=basic_rxn,
        stm=stm,
        sld=sld,
        gas=gas
    )


def build_desc_context(payload: FrontendPayload) -> BackendContextDesc:
    """Build the `context.desc` section from a frontend payload."""
    pheno = payload.phenomenon or {}
    
    # Helper to ensure list of strings
    def _to_list(val: Any) -> List[str]:
        if isinstance(val, list):
            return [str(x) for x in val if x]
        if isinstance(val, str) and val:
            return [val]
        return []

    return BackendContextDesc(
        ac=pheno.get("ac"),
        fp=pheno.get("fp"),
        mt=_to_list(pheno.get("mt")),
        me=_to_list(pheno.get("me")),
        rxn=pheno.get("rxn", {}),
        param_law=pheno.get("param_law", {})
    )


def translate_frontend_to_backend(payload: FrontendPayload) -> BackendContext:
    """Full translation from frontend payload to backend context."""
    return BackendContext(
        type="dynamic",
        basic=build_basic_context(payload),
        desc=build_desc_context(payload)
    )
