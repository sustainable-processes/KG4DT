from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .graphdb_model_utils import SPARQL_PREFIX
from .graphdb_model_utils import query_var as gq_query_var
from ..services.graphdb import GraphDBClient


def _local(x: Optional[str]) -> Optional[str]:
    if not x:
        return None
    return x.split('#')[-1]


def query_law(client: GraphDBClient) -> Dict[str, Any]:
    """Return a minimal map of laws with variables and associated phenomenon.

    Output structure:
      { law_name: {"cls": "Law", "vars": [..], "opt_vars": [..], "pheno": <str|None>,
                   "assoc_gas_law": <str|None>, "assoc_sld_law": <str|None>} }
    """
    law_dict: Dict[str, Any] = {}

    # Base law + variables + associated phenomenon + optional associated gas/solid laws
    sparql = (
        f"{SPARQL_PREFIX}"  # reuse prefixes from model utils
        "select ?l ?v ?p ?agl ?asl where {"
        "?l rdf:type ontomo:Law. "
        "?l ontomo:hasModelVariable ?v. "
        "optional{?l ontomo:isAssociatedWith ?p}. "
        "optional{?l ontomo:hasAssociatedGasLaw ?agl}. "
        "optional{?l ontomo:hasAssociatedSolidLaw ?asl}. "
        "}"
    )
    data = client.select(sparql)
    for b in data.get("results", {}).get("bindings", []):
        l_uri = b.get("l", {}).get("value")
        v_uri = b.get("v", {}).get("value")
        p_uri = b.get("p", {}).get("value")
        agl_uri = b.get("agl", {}).get("value")
        asl_uri = b.get("asl", {}).get("value")
        def local(x: Optional[str]) -> Optional[str]:
            if not x:
                return None
            return x.split("#")[-1]
        l = local(l_uri)
        v = local(v_uri)
        p = local(p_uri)
        agl = local(agl_uri)
        asl = local(asl_uri)
        if not l or not v:
            continue
        if l not in law_dict:
            law_dict[l] = {"cls": "Law", "vars": [], "opt_vars": [], "pheno": p, "assoc_gas_law": agl, "assoc_sld_law": asl}
        if v not in law_dict[l]["vars"]:
            law_dict[l]["vars"].append(v)
        if p and law_dict[l]["pheno"] is None:
            law_dict[l]["pheno"] = p
        if agl and law_dict[l].get("assoc_gas_law") is None:
            law_dict[l]["assoc_gas_law"] = agl
        if asl and law_dict[l].get("assoc_sld_law") is None:
            law_dict[l]["assoc_sld_law"] = asl

    # Optional variables
    sparql_opt = (
        f"{SPARQL_PREFIX}"
        "select ?l ?ov where {"
        "?l rdf:type ontomo:Law. "
        "optional{?l ontomo:hasOptionalModelVariable ?ov}. "
        "}"
    )
    data_opt = client.select(sparql_opt)
    for b in data_opt.get("results", {}).get("bindings", []):
        l_uri = b.get("l", {}).get("value")
        ov_uri = b.get("ov", {}).get("value")
        def local(x: Optional[str]) -> Optional[str]:
            if not x:
                return None
            return x.split("#")[-1]
        l = local(l_uri)
        ov = local(ov_uri)
        if not l or not ov:
            continue
        law_dict.setdefault(l, {"cls": "Law", "vars": [], "opt_vars": [], "pheno": None, "assoc_gas_law": None, "assoc_sld_law": None})
        if ov not in law_dict[l]["opt_vars"]:
            law_dict[l]["opt_vars"].append(ov)

    # Deterministic ordering
    out = {k: law_dict[k] for k in sorted(law_dict.keys())}
    for v in out.values():
        v["vars"] = sorted(v.get("vars", []))
        v["opt_vars"] = sorted(v.get("opt_vars", []))
    return out


def query_symbol(client: GraphDBClient, unit: str) -> Optional[str]:
    """Resolve a unit symbol string (MathML) for a Unit local name (case-insensitive)."""
    if unit is None or str(unit).strip() == "":
        return None
    u = str(unit).strip()
    sparql = (
        f"{SPARQL_PREFIX}"
        "select ?u ?s where {"
        "?u rdf:type ontomo:Unit. "
        "optional{?u ontomo:hasSymbol ?s}. "
        f"FILTER(regex(str(?u), '#{u}$', 'i')). "
        "}"
    )
    data = client.select(sparql)
    for b in data.get("results", {}).get("bindings", []):
        s_val = b.get("s", {}).get("value")
        if not s_val:
            continue
        # strip quotes and xmlns to align with existing behavior
        s = s_val
        if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
            s = s[1:-1]
        s = s.replace(" xmlns=\"http://www.w3.org/1998/Math/MathML\"", "")
        return s
    return None


def query_symbols(client: GraphDBClient, units: List[str]) -> Dict[str, Any]:
    """Batch resolve symbols for a list of unit names."""
    symbols: Dict[str, Any] = {}
    not_found: List[str] = []
    for u in units:
        sym = query_symbol(client, u)
        if sym is None:
            symbols[u] = None
            not_found.append(u)
        else:
            symbols[u] = sym
    result: Dict[str, Any] = {"symbols": symbols}
    if not_found:
        result["not_found"] = not_found
    return result


def build_triplets(client: GraphDBClient) -> Dict[str, Any]:
    """Build simple triplets view using variables and laws.

    Structure:
      {"triplets": {"var": {..}, "law": {..}, "relationship": [[s,p,o], ...]}}
    """
    # Vars
    sparql_vars = (
        f"{SPARQL_PREFIX}"
        "select ?v ?l where {"
        "?v rdf:type ?t. "
        "FILTER(?t IN (ontomo:Constant, ontomo:RateVariable, ontomo:StateVariable, ontomo:FlowParameter, ontomo:PhysicsParameter, ontomo:ReactionParameter, ontomo:OperationParameter, ontomo:StructureParameter, ontomo:MassTransportParameter)). "
        "optional{?l rdf:type ontomo:Law. ?l ontomo:hasModelVariable ?v}. "
        "}"
    )
    data_v = client.select(sparql_vars)
    var_set: set[str] = set()
    rel: List[List[str]] = []
    def local(x: Optional[str]) -> Optional[str]:
        if not x:
            return None
        return x.split('#')[-1]
    for b in data_v.get("results", {}).get("bindings", []):
        v = local(b.get("v", {}).get("value"))
        l = local(b.get("l", {}).get("value"))
        if v:
            var_set.add(v)
        if v and l:
            rel.append([v, "hasLaw", l])
            rel.append([l, "hasModelVariable", v])

    # Laws set
    sparql_l = f"{SPARQL_PREFIX}select ?l where {{ ?l rdf:type ontomo:Law. }}"
    data_l = client.select(sparql_l)
    law_set: set[str] = set()
    for b in data_l.get("results", {}).get("bindings", []):
        l = local(b.get("l", {}).get("value"))
        if l:
            law_set.add(l)

    var_nodes = {name: {} for name in sorted(var_set)}
    law_nodes = {name: {} for name in sorted(law_set)}

    # Deduplicate rels deterministically
    seen = set()
    rel_unique: List[List[str]] = []
    for s, p, o in rel:
        t = (s, p, o)
        if t in seen:
            continue
        seen.add(t)
        rel_unique.append([s, p, o])

    return {"triplets": {"var": var_nodes, "law": law_nodes, "relationship": rel_unique}}


# --------------------------
# Operation Parameters (op_param)
# --------------------------

def _ensure_dict(d: Any) -> Dict[str, Any]:
    return d if isinstance(d, dict) else {}


def _ensure_idx_map(m: Any) -> Dict[str, Dict[str, List[str]]]:
    if not isinstance(m, dict):
        return {}
    out: Dict[str, Dict[str, List[str]]] = {}
    for k, v in m.items():
        if not isinstance(v, dict):
            continue
        spc = v.get("spc")
        if spc is None:
            out[str(k)] = {"spc": []}
        elif isinstance(spc, list):
            out[str(k)] = {"spc": [str(x).strip() for x in spc if x is not None and str(x).strip() != ""]}
        else:
            s = str(spc).strip()
            out[str(k)] = {"spc": [s] if s else []}
    return out


def _norm_str(x: Any) -> Optional[str]:
    return str(x).strip() if isinstance(x, (str, int, float)) else None


def _norm_list(val: Any) -> List[str]:
    if val is None:
        return []
    if isinstance(val, list):
        items = val
    else:
        items = [val]
    out: List[str] = []
    for x in items:
        s = _norm_str(x)
        if s:
            out.append(s)
    return out


def normalize_context(context: Dict[str, Any]) -> Dict[str, Any]:
    basic_in = _ensure_dict(context.get("basic"))
    desc_in = _ensure_dict(context.get("desc"))

    basic_norm: Dict[str, Any] = {
        "stm": _ensure_idx_map(_ensure_dict(basic_in.get("stm"))),
        "gas": _ensure_idx_map(_ensure_dict(basic_in.get("gas"))),
        "sld": _ensure_idx_map(_ensure_dict(basic_in.get("sld"))),
    }
    if isinstance(basic_in.get("spc"), list):
        basic_norm["spc"] = [str(x).strip() for x in basic_in.get("spc") if x is not None and str(x).strip()]
    if isinstance(basic_in.get("rxn"), list):
        basic_norm["rxn"] = [str(x).strip() for x in basic_in.get("rxn") if x is not None and str(x).strip()]

    desc_norm: Dict[str, Any] = {
        "ac": _norm_str(desc_in.get("ac")),
        "fp": _norm_str(desc_in.get("fp")),
        "mt": _norm_list(desc_in.get("mt")),
        "me": _norm_list(desc_in.get("me")),
        "rxn": {},
        "param_law": {},
    }

    rxn = desc_in.get("rxn")
    if isinstance(rxn, dict):
        for rk, rv in rxn.items():
            lst = _norm_list(rv)
            if lst:
                desc_norm["rxn"][str(rk).strip()] = lst
    elif isinstance(rxn, list):
        for item in rxn:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                r = _norm_str(item[0])
                ph = _norm_str(item[1])
                if r and ph:
                    desc_norm["rxn"].setdefault(r, []).append(ph)
    elif isinstance(rxn, (str, int, float)):
        r = _norm_str(rxn)
        if r:
            desc_norm["rxn"][r] = []

    pl = desc_in.get("param_law")
    if isinstance(pl, dict):
        for pk, pv in pl.items():
            ps = _norm_str(pk)
            ls = _norm_str(pv)
            if ps and ls:
                desc_norm["param_law"][ps] = ls
    elif isinstance(pl, list):
        for item in pl:
            if isinstance(item, dict):
                for pk, pv in item.items():
                    ps = _norm_str(pk)
                    ls = _norm_str(pv)
                    if ps and ls:
                        desc_norm["param_law"][ps] = ls

    return {"basic": basic_norm, "desc": desc_norm}


def query_op_param(client: GraphDBClient, context: Dict[str, Any]) -> List[List[Optional[str]]]:
    """Derive Operation Parameters for a given modeling context.

    Returns a deterministic list of [name, idx1, idx2, idx3, idx4].
    """
    if not isinstance(context, dict):
        return []

    ctx = normalize_context(context)
    basic = ctx.get("basic", {})
    desc = ctx.get("desc", {})

    # Prepare convenience variables
    stms = list(basic.get("stm", {}).keys())
    gass = list(basic.get("gas", {}).keys())
    slds = list(basic.get("sld", {}).keys())

    ac = desc.get("ac")
    fp = desc.get("fp")
    mts: List[str] = desc.get("mt", []) or []
    mes: List[str] = desc.get("me", []) or []
    param_law_map: Dict[str, str] = desc.get("param_law", {}) or {}
    rxn_dict: Dict[str, List[str]] = desc.get("rxn", {}) or {}

    # Base datasets
    laws = query_law(client)
    vars_map = gq_query_var(client)

    # Collect vars by descriptor relationships (parity with Flask logic)
    ac_vars: set[str] = set()
    ac_opt_vars: set[str] = set()
    if ac:
        for law_dict in laws.values():
            if law_dict.get("pheno") == ac:
                for v in law_dict.get("vars", []):
                    ac_vars.add(v)
                for v in law_dict.get("opt_vars", []):
                    ac_opt_vars.add(v)

    fp_vars: set[str] = set()
    if fp and ac_vars:
        for law_name, law_dict in laws.items():
            # if any ac_var has this law in its var.laws, and law is FP
            try:
                if any(law_name in (vars_map.get(var, {}).get("laws") or []) for var in ac_vars):
                    if law_dict.get("pheno") == fp:
                        for v in law_dict.get("vars", []):
                            fp_vars.add(v)
            except Exception:
                continue

    mt_vars: set[str] = set()
    if mts and ac_opt_vars:
        for law_name, law_dict in laws.items():
            try:
                if any(law_name in (vars_map.get(var, {}).get("laws") or []) for var in ac_opt_vars):
                    if law_dict.get("pheno") in mts:
                        for v in law_dict.get("vars", []):
                            mt_vars.add(v)
            except Exception:
                continue

    me_vars: set[str] = set()
    if mts and mes and mt_vars:
        for law_name, law_dict in laws.items():
            try:
                if any(law_name in (vars_map.get(var, {}).get("laws") or []) for var in mt_vars):
                    if law_dict.get("pheno") in mes:
                        for v in law_dict.get("vars", []):
                            me_vars.add(v)
            except Exception:
                continue

    assoc_gas_vars: set[str] = set()
    if mts and gass and ac_opt_vars:
        for law_name, law_dict in laws.items():
            try:
                if any(law_name in (vars_map.get(var, {}).get("laws") or []) for var in ac_opt_vars):
                    if law_dict.get("pheno") in mts:
                        agl = law_dict.get("assoc_gas_law")
                        if agl and agl in laws and basic.get("gas"):
                            for v in laws[agl].get("vars", []):
                                assoc_gas_vars.add(v)
            except Exception:
                continue

    assoc_sld_vars: set[str] = set()
    if mts and slds and ac_opt_vars:
        for law_name, law_dict in laws.items():
            try:
                if any(law_name in (vars_map.get(var, {}).get("laws") or []) for var in ac_opt_vars):
                    if law_dict.get("pheno") in mts:
                        asl = law_dict.get("assoc_sld_law")
                        if asl and asl in laws and basic.get("sld"):
                            for v in laws[asl].get("vars", []):
                                assoc_sld_vars.add(v)
            except Exception:
                continue

    param_law_vars: set[str] = set()
    for l in param_law_map.values():
        if l in laws:
            for v in laws[l].get("vars", []):
                param_law_vars.add(v)

    rxn_var_dict: Dict[str, set[str]] = {r: set() for r in rxn_dict}
    for rxn, rxn_phenos in rxn_dict.items():
        for law_name, law_meta in laws.items():
            if law_meta.get("pheno") in rxn_phenos:
                for v in law_meta.get("vars", []):
                    rxn_var_dict[rxn].add(v)
                    # include variables of the laws that this variable participates in
                    for var_law in (vars_map.get(v, {}).get("laws") or []):
                        for vv in laws.get(var_law, {}).get("vars", []):
                            rxn_var_dict[rxn].add(vv)

    desc_vars: set[str] = set()
    desc_vars.update(ac_vars)
    desc_vars.update(fp_vars)
    desc_vars.update(mt_vars)
    desc_vars.update(me_vars)
    desc_vars.update(assoc_gas_vars)
    desc_vars.update(assoc_sld_vars)
    desc_vars.update(param_law_vars)
    for s in rxn_var_dict.values():
        desc_vars.update(s)

    # Filter only OperationParameter variables without own laws
    op_param_entries: List[List[Optional[str]]] = []
    for var in sorted(desc_vars):
        vmeta = vars_map.get(var) or {}
        if not vmeta:
            continue
        if vmeta.get("cls") != "OperationParameter":
            continue
        if vmeta.get("laws"):
            # skip parameters that already have own laws
            continue
        dims = set(vmeta.get("dims") or [])
        if dims == set():
            op_param_entries.append([var, None, None, None, None])
        elif dims == {"Stream"}:
            for stm in stms:
                op_param_entries.append([var, None, stm, None, None])
        elif dims == {"Gas"}:
            for gas in gass:
                op_param_entries.append([var, gas, None, None, None])
        elif dims == {"Solid"}:
            for sld in slds:
                op_param_entries.append([var, sld, None, None, None])
        elif dims == {"Species", "Stream"}:
            for stm in stms:
                for spc in basic.get("stm", {}).get(stm, {}).get("spc", []) or []:
                    op_param_entries.append([var, None, stm, None, spc])
        elif dims == {"Species", "Gas"}:
            for gas in gass:
                for spc in basic.get("gas", {}).get(gas, {}).get("spc", []) or []:
                    op_param_entries.append([var, gas, None, None, spc])
        elif dims == {"Species", "Solid"}:
            for sld in slds:
                for spc in basic.get("sld", {}).get(sld, {}).get("spc", []) or []:
                    op_param_entries.append([var, sld, None, None, spc])
        else:
            # Unknown dimensioning; default to global to avoid omission
            op_param_entries.append([var, None, None, None, None])

    # Deterministic sort
    op_param_entries.sort(key=lambda x: (
        str(x[0]),
        str(x[1]) if x[1] is not None else "",
        str(x[2]) if x[2] is not None else "",
        str(x[3]) if x[3] is not None else "",
        str(x[4]) if x[4] is not None else "",
    ))

    return op_param_entries
