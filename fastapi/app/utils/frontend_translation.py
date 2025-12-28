from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional
from ..schemas.translation import FrontendPayload, BackendContextBasic, BackendContextDesc, BackendContext


def build_basic_context(payload: FrontendPayload) -> BackendContextBasic:
    """Build the `context.basic` section from a frontend payload."""
    chemistry = payload.chemistry or {}
    species = chemistry.get("species") or []
    reactions = chemistry.get("reactions") or []

    # basic.spc (full objects, preserving order)
    basic_spc = []
    seen_spc = set()
    for s in species:
        if isinstance(s, dict):
            sid = s.get("id")
            if sid not in seen_spc:
                basic_spc.append(s)
                seen_spc.add(sid)

    # basic.rxn (full objects, preserving order)
    basic_rxn = []
    seen_rxn = set()
    for r in reactions:
        if isinstance(r, dict):
            # Use stoich as a proxy for identity if id is missing
            rid = r.get("id") or r.get("stoich")
            if rid not in seen_rxn:
                basic_rxn.append(r)
                seen_rxn.add(rid)

    # Inputs & Utilities
    inputs: Dict[str, Any] = payload.input or {}
    utilities: Dict[str, Any] = payload.utility or {}
    
    stm: Dict[str, Any] = {}
    sld: Dict[str, Any] = {}
    gas: Dict[str, Any] = {}

    # Combined processing for input and utility
    combined_items = {**inputs, **utilities}
    for name, item in combined_items.items():
        if not isinstance(item, dict):
            continue
        typ = (item.get("type") or "").lower()
        
        # Phases mapping: Key = phases, value = array of species ID/name.
        # Desired output format: "spc": [ {"phase 1": ["water", "solvent"]} ]
        phases = item.get("phases")
        spc_entry = []
        if isinstance(phases, dict):
            spc_entry = [phases]
        elif isinstance(phases, list):
            spc_entry = phases
        
        rxn_local = []
        chem_local = item.get("chemistry") if isinstance(item.get("chemistry"), dict) else {}
        rxn_raw = chem_local.get("reaction")
        if isinstance(rxn_raw, list):
            for r in rxn_raw:
                if isinstance(r, str):
                    rxn_local.append({"stoich": r})
                else:
                    rxn_local.append(r)

        entry: Dict[str, Any] = {"spc": spc_entry}
        if rxn_local:
            entry["rxn"] = rxn_local

        if typ in ["stream", "steam"]:
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
    # Try to extract from reactor phenomenon
    reactor = payload.reactor or {}
    # Find the first vessel or use 'reactor vessel'
    vessel = reactor.get("reactor vessel")
    if not vessel and reactor:
        # Fallback to first available vessel if 'reactor vessel' key is not present
        vessel = next(iter(reactor.values())) if isinstance(reactor, dict) and reactor else {}
    
    pheno = vessel.get("phenomenon") if isinstance(vessel, dict) else {}
    
    # Fallback to payload.phenomenon
    if not pheno:
        pheno = payload.phenomenon or {}

    ac = pheno.get("mass accumulation") or pheno.get("ac")
    if isinstance(ac, str):
        ac = ac.capitalize()
    
    fp = pheno.get("flow pattern") or pheno.get("fp")
    if isinstance(fp, str):
        # well_mixed -> Well_Mixed
        fp = "_".join(word.capitalize() for word in fp.split("_"))

    # Extract from model
    model = payload.model or {}
    mt = model.get("mass_transport") or []
    me = model.get("mass_equilibrium") or []
    
    param_law_raw = model.get("laws") or {}
    param_law = {}
    if isinstance(param_law_raw, dict):
        for k, v in param_law_raw.items():
            if isinstance(v, list) and v:
                param_law[k] = v[0]
            elif isinstance(v, str):
                param_law[k] = v

    return BackendContextDesc(
        ac=ac,
        fp=fp,
        mt=mt,
        me=me,
        rxn={},
        param_law=param_law
    )


def translate_frontend_to_backend(payload: FrontendPayload) -> BackendContext:
    """Full translation from frontend payload to backend context."""
    return BackendContext(
        type="dynamic",
        basic=build_basic_context(payload),
        desc=build_desc_context(payload),
        info={
            "st": {},
            "spc": {},
            "stm": {},
            "sld": {},
            "gas": {},
            "mt": {},
            "me": {},
            "rxn": {}
        }
    )
