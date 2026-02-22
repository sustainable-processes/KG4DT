from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional
from ..schemas.translation import FrontendPayload, BackendContextBasic, BackendContextDesc, BackendContext

_INFO_REQUIRED_KEYS = {"type", "reactor", "input", "utility", "chemistry", "kinetics", "model"}


def _normalize_list(val: Any) -> List[str]:
    if val is None:
        return []
    if isinstance(val, list):
        return [str(x).strip() for x in val if x is not None and str(x).strip() != ""]
    if isinstance(val, dict):
        return [str(x).strip() for x in val.keys() if x is not None and str(x).strip() != ""]
    s = str(val).strip()
    return [s] if s else []


@dataclass
class InfoContextView:
    """Parsed view of the frontend context for query_info."""

    spcs: List[str] = field(default_factory=list)
    stms: List[str] = field(default_factory=list)
    gass: List[str] = field(default_factory=list)
    slds: List[str] = field(default_factory=list)
    stm2spcs: Dict[str, List[str]] = field(default_factory=dict)
    gas2spcs: Dict[str, List[str]] = field(default_factory=dict)
    sld2spcs: Dict[str, List[str]] = field(default_factory=dict)
    rxn_phenos: Dict[str, List[str]] = field(default_factory=dict)
    ac_pheno: Optional[str] = None
    fp_pheno: Optional[str] = None
    mt_phenos: List[str] = field(default_factory=list)
    me_phenos: List[str] = field(default_factory=list)
    model_laws: Dict[str, str] = field(default_factory=dict)

    @staticmethod
    def is_frontend_context(context: Dict[str, Any]) -> bool:
        if not isinstance(context, dict):
            return False
        return _INFO_REQUIRED_KEYS.issubset(context.keys())

    @classmethod
    def from_frontend_context(cls, context: Dict[str, Any]) -> "InfoContextView":
        view = cls()

        reactor_block = context.get("reactor") or {}
        reactor_key = next(iter(reactor_block.keys()), None) if isinstance(reactor_block, dict) else None
        reactor_dict = reactor_block.get(reactor_key, {}) if reactor_key else {}

        view.spcs = [
            spc_dict.get("id")
            for spc_dict in context.get("chemistry", {}).get("species", []) or []
            if isinstance(spc_dict, dict) and spc_dict.get("id")
        ]

        for src in reactor_dict.get("source", []) or []:
            src_info = context.get("input", {}).get(src, {})
            if isinstance(src_info, dict) and src_info.get("type") == "Stream":
                view.stms.append(src)
                view.stm2spcs[src] = _normalize_list(src_info.get("species"))

        if reactor_dict.get("operation", {}).get("Has_Liquid_Input"):
            for liq, liq_dict in (reactor_dict.get("liquid") or {}).items():
                view.stms.append(liq)
                if isinstance(liq_dict, dict):
                    view.stm2spcs[liq] = _normalize_list(liq_dict.get("species"))

        if reactor_dict.get("operation", {}).get("Has_Solid_Input"):
            for sld, sld_dict in (reactor_dict.get("solid") or {}).items():
                view.slds.append(sld)
                if isinstance(sld_dict, dict):
                    view.sld2spcs[sld] = _normalize_list(sld_dict.get("species"))

        for src in reactor_dict.get("source", []) or []:
            src_info = context.get("input", {}).get(src, {})
            if isinstance(src_info, dict) and src_info.get("type") == "Gas Flow":
                view.gass.append(src)
                op_info = src_info.get("operation", {})
                if isinstance(op_info, dict):
                    view.gas2spcs[src] = _normalize_list(op_info.get("species"))

        view.ac_pheno = reactor_dict.get("phenomenon", {}).get("Accumulation")
        model = context.get("model", {}) if isinstance(context.get("model"), dict) else {}
        view.fp_pheno = model.get("Flow_Pattern")
        view.mt_phenos = _normalize_list(model.get("Mass_Transport"))
        view.me_phenos = _normalize_list(model.get("Mass_Equilibrium"))
        view.model_laws = {k: v for k, v in (model.get("laws") or {}).items() if v}

        for rxn_entry in context.get("kinetics", []) or []:
            if not isinstance(rxn_entry, dict):
                continue
            rxn_map = rxn_entry.get("elementary") if rxn_entry.get("elementary") else rxn_entry.get("stoich")
            if not isinstance(rxn_map, dict):
                continue
            for rxn, rxn_phenos in rxn_map.items():
                view.rxn_phenos[rxn] = _normalize_list(rxn_phenos)

        return view


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
