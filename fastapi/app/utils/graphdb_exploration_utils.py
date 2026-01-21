from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple, Set

from ..services.graphdb import GraphDBClient
from .graphdb_model_utils import query_var as _query_var, query_unit as _query_unit

# RDF prefixes matching backend/config.py
PREFIX_RDF = "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>"
# Keep OntoMo prefix aligned with the ontology file used in this repo
PREFIX_ONTOMO = (
    "PREFIX ontomo: <https://raw.githubusercontent.com/"
    "sustainable-processes/KG4DT/refs/heads/dev-alkyne-hydrogenation/ontology/OntoMo.owl#>"
)
PREFIX = "\n".join([PREFIX_RDF, PREFIX_ONTOMO, ""])  # trailing newline


def _extract_local_name(uri: str) -> str:
    """Return the fragment after '#' or the last path segment."""
    if not uri:
        return uri
    if "#" in uri:
        return uri.rsplit("#", 1)[-1]
    return uri.rstrip("/").rsplit("/", 1)[-1]


def query_ac(client: GraphDBClient) -> List[str]:
    """Query Accumulation categories.

    Returns a sorted list of accumulation names.
    """
    sparql = f"{PREFIX}SELECT ?ac WHERE {{ ?ac rdf:type ontomo:Accumulation. }}"
    res = client.select(sparql)
    out: List[str] = []
    for b in res.get("results", {}).get("bindings", []):
        uri = b.get("ac", {}).get("value")
        if uri:
            out.append(_extract_local_name(uri))
    return sorted(set(out))


# The following functions provide scaffolding for more complex queries.
# They return structured 501-style responses to indicate that the functionality
# is not yet implemented in the FastAPI service. This keeps the API surface
# compatible with the Flask version and allows incremental migration.

def query_pheno(client: GraphDBClient) -> Dict[str, Any]:
    """Query Phenomena and their relations.

    Returns a dictionary keyed by phenomenon local name with structure:
      {
        <name>: {
          "cls": <ClassName>,
          "fps": [<FlowPattern names>],
          "mts": [<MassTransportPhenomenon names>],
          "mes": [<MassEquilibriumPhenomenon names>]
        },
        ...
      }
    Mirrors Flask PhenomenonService.query_pheno output.
    """
    pheno: Dict[str, Dict[str, Any]] = {}

    # Iterate across the same classes used by the Flask backend
    pheno_classes: List[str] = [
        "Accumulation",
        "FlowPattern",
        "MassTransportPhenomenon",
        "MassEquilibriumPhenomenon",
        "ReactionPhenomenon",
    ]

    for pheno_class in pheno_classes:
        sparql = (
            f"{PREFIX}"
            "select ?p ?fp ?mtp ?mep where {"
            f"?p rdf:type ontomo:{pheno_class}. "
            "optional{?p ontomo:relatesToFlowPattern ?fp}. "
            "optional{?p ontomo:relatesToMassTransportPhenomenon ?mtp}. "
            "optional{?p ontomo:relatesToMassEquilibriumPhenomenon ?mep}. "
            "}"
        )
        data = client.select(sparql)
        for b in data.get("results", {}).get("bindings", []):
            p_uri = b.get("p", {}).get("value")
            fp_uri = b.get("fp", {}).get("value")
            mtp_uri = b.get("mtp", {}).get("value")
            mep_uri = b.get("mep", {}).get("value")

            p = _extract_local_name(p_uri) if p_uri else None
            if not p:
                continue
            fp = _extract_local_name(fp_uri) if fp_uri else None
            mtp = _extract_local_name(mtp_uri) if mtp_uri else None
            mep = _extract_local_name(mep_uri) if mep_uri else None

            if p not in pheno:
                pheno[p] = {"cls": pheno_class, "fps": [], "mts": [], "mes": []}

            if fp and fp not in pheno[p]["fps"]:
                pheno[p]["fps"].append(fp)
            if mtp and mtp not in pheno[p]["mts"]:
                pheno[p]["mts"].append(mtp)
            if mep and mep not in pheno[p]["mes"]:
                pheno[p]["mes"].append(mep)

    # sort keys and lists for deterministic output
    pheno_sorted = {k: pheno[k] for k in sorted(pheno.keys())}
    for v in pheno_sorted.values():
        v["fps"] = sorted(v.get("fps", []))
        v["mts"] = sorted(v.get("mts", []))
        v["mes"] = sorted(v.get("mes", []))
    return pheno_sorted


def query_fp_by_ac(client: GraphDBClient, ac: str) -> List[str]:
    """Return flow patterns associated with a given Accumulation name.

    Matching is case-insensitive on the local name of the Accumulation individual.
    Output: sorted unique list of FlowPattern local names.
    """
    if ac is None or str(ac).strip() == "":
        return []
    ac_str = str(ac).strip()
    sparql = (
        f"{PREFIX}"
        "select ?p ?rp where {"
        "?p rdf:type ontomo:Accumulation. "
        "optional{?p ontomo:relatesToFlowPattern ?rp}. "
        f"FILTER(regex(str(?p), '#{ac_str}$', 'i')). "
        "}"
    )
    data = client.select(sparql)
    fps: set[str] = set()
    for b in data.get("results", {}).get("bindings", []):
        rp_uri = b.get("rp", {}).get("value")
        if rp_uri:
            fps.add(_extract_local_name(rp_uri))
    return sorted(fps)


def query_mt_by_fp(client: GraphDBClient, fp: str) -> List[str]:
    """Return mass transport phenomena associated with a given FlowPattern name.

    Matching is case-insensitive on the FlowPattern IRI tail.
    Output: sorted unique list of MassTransportPhenomenon local names.
    """
    if fp is None or str(fp).strip() == "":
        return []
    fp_str = str(fp).strip()
    sparql = (
        f"{PREFIX}"
        "select ?fp ?mt where {"
        "?fp rdf:type ontomo:FlowPattern. "
        "optional{?fp ontomo:relatesToMassTransportPhenomenon ?mt}. "
        f"FILTER(regex(str(?fp), '#{fp_str}$', 'i')). "
        "}"
    )
    data = client.select(sparql)
    mts: set[str] = set()
    for b in data.get("results", {}).get("bindings", []):
        mt_uri = b.get("mt", {}).get("value")
        if mt_uri:
            mts.add(_extract_local_name(mt_uri))
    return sorted(mts)


def query_me_by_mt(client: GraphDBClient, mt: str) -> List[str]:
    """Return mass equilibrium phenomena associated with a given MassTransportPhenomenon name.

    Matching is case-insensitive on the MassTransportPhenomenon IRI tail.
    Output: sorted unique list of MassEquilibriumPhenomenon local names.
    """
    if mt is None or str(mt).strip() == "":
        return []
    mt_str = str(mt).strip()
    sparql = (
        f"{PREFIX}"
        "select ?mt ?me where {"
        "?mt rdf:type ontomo:MassTransportPhenomenon. "
        f"FILTER(regex(str(?mt), '#{mt_str}$', 'i')). "
        "?me rdf:type ontomo:MassEquilibriumPhenomenon. "
        "?mt ontomo:relatesToMassEquilibriumPhenomenon ?me. "
        "}"
    )
    data = client.select(sparql)
    mes: set[str] = set()
    for b in data.get("results", {}).get("bindings", []):
        me_uri = b.get("me", {}).get("value")
        if me_uri:
            mes.add(_extract_local_name(me_uri))
    return sorted(mes)


def _local(name_or_uri: Optional[str]) -> Optional[str]:
    if not name_or_uri:
        return None
    return _extract_local_name(name_or_uri)


def _query_laws_basic(client: GraphDBClient) -> Dict[str, Dict[str, Any]]:
    """Return minimal law metadata required for param_law and query_info computation.

    Output: { 
        law_name: {
            "pheno": <phenomenon or None>, 
            "vars": List[str],
            "opt_vars": List[str],
            "assoc_gas_law": <law_name or None>,
            "assoc_sld_law": <law_name or None>,
        } 
    }
    """
    laws: Dict[str, Dict[str, Any]] = {}
    sparql = (
        f"{PREFIX}"
        "select ?l ?v ?p ?ov ?agl ?asl where {"
        "?l rdf:type ontomo:Law. "
        "optional{?l ontomo:hasModelVariable ?v}. "
        "optional{?l ontomo:isAssociatedWith ?p}. "
        "optional{?l ontomo:hasOptionalModelVariable ?ov}. "
        "optional{?l ontomo:hasAssociatedGasLaw ?agl}. "
        "optional{?l ontomo:hasAssociatedSolidLaw ?asl}. "
        "}"
    )
    data = client.select(sparql)
    for b in data.get("results", {}).get("bindings", []):
        l = _local(b.get("l", {}).get("value"))
        v = _local(b.get("v", {}).get("value"))
        p = _local(b.get("p", {}).get("value"))
        ov = _local(b.get("ov", {}).get("value"))
        agl = _local(b.get("agl", {}).get("value"))
        asl = _local(b.get("asl", {}).get("value"))
        
        if not l:
            continue
        if l not in laws:
            laws[l] = {
                "pheno": p, 
                "vars": set(), 
                "opt_vars": set(),
                "assoc_gas_law": agl,
                "assoc_sld_law": asl
            }
        if v:
            laws[l]["vars"].add(v)
        if ov:
            laws[l]["opt_vars"].add(ov)
        if p and not laws[l]["pheno"]:
            laws[l]["pheno"] = p
        if agl and not laws[l]["assoc_gas_law"]:
            laws[l]["assoc_gas_law"] = agl
        if asl and not laws[l]["assoc_sld_law"]:
            laws[l]["assoc_sld_law"] = asl

    # convert sets to sorted lists for stability
    for k in laws:
        laws[k]["vars"] = sorted(list(laws[k]["vars"]))
        laws[k]["opt_vars"] = sorted(list(laws[k]["opt_vars"]))
        
    return laws


def _normalize_list(val: Any) -> List[str]:
    if val is None:
        return []
    if isinstance(val, list):
        return [str(x).strip() for x in val if x is not None and str(x).strip() != ""]
    if isinstance(val, dict):
        return [str(x).strip() for x in val.keys() if x is not None and str(x).strip() != ""]
    s = str(val).strip()
    return [s] if s else []


# ------------------------------
# Complexity: set-based indices
# ------------------------------
def _build_indices(
    laws_dict: Dict[str, Dict[str, Any]],
    vars_dict: Dict[str, Dict[str, Any]],
) -> Tuple[
    Dict[str, Set[str]],  # laws_by_pheno
    Dict[str, Set[str]],  # vars_by_law
    Dict[str, Set[str]],  # laws_by_var
    Dict[str, Set[str]],  # vars_by_pheno
]:
    """Build fast set-based indices for O(1) membership and fast unions.

    laws_by_pheno: pheno -> set(law)
    vars_by_law:   law   -> set(var)
    laws_by_var:   var   -> set(law)
    vars_by_pheno: pheno -> set(var)
    """
    laws_by_pheno: Dict[str, Set[str]] = {}
    vars_by_law: Dict[str, Set[str]] = {}
    laws_by_var: Dict[str, Set[str]] = {}

    for law, ld in laws_dict.items():
        p = ld.get("pheno")
        if p:
            laws_by_pheno.setdefault(p, set()).add(law)
        vars_by_law[law] = set(ld.get("vars", []) or [])

    for v, vd in vars_dict.items():
        laws_by_var[v] = set(vd.get("laws", []) or [])

    vars_by_pheno: Dict[str, Set[str]] = {}
    for p, law_set in laws_by_pheno.items():
        # union vars for all laws in this pheno
        agg: Set[str] = set()
        for l in law_set:
            agg |= vars_by_law.get(l, set())
        vars_by_pheno[p] = agg

    return laws_by_pheno, vars_by_law, laws_by_var, vars_by_pheno


def query_param_law(client: GraphDBClient, desc: Dict[str, Any]) -> Dict[str, Any]:
    """Compute parameter->law mapping constrained by selected phenomena.

    desc may contain any of: ac, fp, mt, me with string or list values.
    Output: { parameter: [law1, law2, ...] } with deterministic ordering.
    """
    if not isinstance(desc, dict):
        return {}

    # Normalize filters
    ac_list = _normalize_list(desc.get("ac"))
    fp_list = _normalize_list(desc.get("fp"))
    mt_list = _normalize_list(desc.get("mt"))
    me_list = _normalize_list(desc.get("me"))

    # Base datasets
    vars_dict = _query_var(client)  # var -> {laws: [...], ...}
    laws_dict = _query_laws_basic(client)  # law -> {pheno, vars}

    # Build indices for faster set operations (complexity improvement)
    laws_by_pheno, vars_by_law, laws_by_var, vars_by_pheno = _build_indices(laws_dict, vars_dict)

    fp_set = set(fp_list)
    mt_set = set(mt_list)
    me_set = set(me_list)

    param_law: Dict[str, List[str]] = {}

    # Helper to add mapping ensuring determinism and uniqueness
    def add_mapping(var: str, law_names: List[str]):
        if not law_names:
            return
        selected = sorted(set(law_names))
        if var in param_law:
            merged = sorted(set(param_law[var] + selected))
            param_law[var] = merged
        else:
            param_law[var] = selected

    # 1) Flow pattern laws subsidiary to mass transport
    #    For each MT pheno, get its vars, then keep only those vars whose own laws intersect FP phenos.
    if mt_set:
        mt_vars = set().union(*(vars_by_pheno.get(p, set()) for p in mt_set)) if mt_set else set()
        for var in mt_vars:
            if var == "Concentration":
                continue
            var_laws = laws_by_var.get(var, set())
            fp_laws_for_var = [l for l in var_laws if laws_dict.get(l, {}).get("pheno") in fp_set]
            if fp_laws_for_var and var not in param_law:
                add_mapping(var, fp_laws_for_var)

    # 2) Flow pattern laws subsidiary to flow pattern
    if fp_set:
        fp_vars = set().union(*(vars_by_pheno.get(p, set()) for p in fp_set))
        for var in fp_vars:
            if var == "Concentration" or var in param_law:
                continue
            var_laws = laws_by_var.get(var, set())
            fp_laws_for_var = [l for l in var_laws if laws_dict.get(l, {}).get("pheno") in fp_set]
            if fp_laws_for_var:
                add_mapping(var, fp_laws_for_var)

    # 3) Mass equilibrium laws filtered from MT
    if mt_set and me_set:
        mt_vars = set().union(*(vars_by_pheno.get(p, set()) for p in mt_set))
        for var in mt_vars:
            if var in param_law:
                continue
            var_laws = laws_by_var.get(var, set())
            me_laws_for_var = [l for l in var_laws if laws_dict.get(l, {}).get("pheno") in me_set]
            if me_laws_for_var:
                add_mapping(var, me_laws_for_var)

    # Sort keys deterministically
    return {k: param_law[k] for k in sorted(param_law.keys())}


def query_rxn(client: GraphDBClient, filters: Optional[Dict[str, Any]] = None) -> Any:
    """List ReactionPhenomenon names; if filters provided, basic filtering may be applied later.
    """
    sparql = f"{PREFIX}select ?p where {{ ?p rdf:type ontomo:ReactionPhenomenon. }}"
    data = client.select(sparql)
    rxns: List[str] = []
    for b in data.get("results", {}).get("bindings", []):
        uri = b.get("p", {}).get("value")
        name = _local(uri)
        if name:
            rxns.append(name)
    rxns = sorted(set(rxns))
    return rxns


def query_rxn_formulas(client: GraphDBClient, rxn_names: List[str]) -> str:
    """Return a combined MathML formula for the selected reaction phenomena.

    The formulas for each phenomenon are joined together (multiplied).
    """
    if not rxn_names:
        return ""

    # Use FILTER IN for multiple names
    names_str = ", ".join([f'"{n}"' for n in rxn_names])
    sparql = (
        f"{PREFIX}"
        "SELECT ?p ?f WHERE {"
        "  ?p rdf:type ontomo:ReactionPhenomenon."
        "  ?l ontomo:isAssociatedWith ?p."
        "  ?l ontomo:hasFormula ?f."
        "  BIND(STRAFTER(STR(?p), '#') AS ?localName)"
        f"  FILTER(?localName IN ({names_str}))"
        "}"
    )

    res = client.select(sparql)
    formulas: List[str] = []

    # Map name -> formula
    name_to_formula: Dict[str, str] = {}
    for b in res.get("results", {}).get("bindings", []):
        p_uri = b.get("p", {}).get("value")
        f_val = b.get("f", {}).get("value")
        name = _extract_local_name(p_uri)
        if name and f_val:
            name_to_formula[name] = f_val

    # Reconstruct in requested order and combine
    for name in rxn_names:
        if name in name_to_formula:
            f = name_to_formula[name]
            # Extract content from <math> if present
            match = re.search(r"<math[^>]*>(.*)</math>", f, re.DOTALL)
            if match:
                formulas.append(match.group(1))
            else:
                formulas.append(f)

    if not formulas:
        return ""

    # Wrap multiple formulas in <mrow> and then in <math>
    combined_content = "".join(formulas)
    return f"<math><mrow>{combined_content}</mrow></math>"


def query_info(client: GraphDBClient, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return a flat list of model parameters based on the provided context.
    
    Restructured for frontend friendliness: returns {"parameters": [...]}
    where each parameter is a flat object with a standardized 5-tuple index.
    """
    if context is None:
        context = {}
    
    basic = context.get("basic", {})
    desc = context.get("desc", {})

    spcs = _normalize_list(basic.get("spc"))
    rxn_names = _normalize_list(basic.get("rxn"))  # actually this is usually from desc.rxn keys
    stms = _normalize_list(basic.get("stm"))
    gass = _normalize_list(basic.get("gas"))
    slds = _normalize_list(basic.get("sld"))

    ac = desc.get("ac")
    fp = desc.get("fp")
    mts = _normalize_list(desc.get("mt"))
    mes = _normalize_list(desc.get("me"))
    param_law = desc.get("param_law", {})
    rxn_dict = desc.get("rxn", {})

    vars_dict = _query_var(client)
    units_dict = _query_unit(client)
    laws = _query_laws_basic(client)

    # 1. Resolve which variables are active based on phenomena selection (Logic from PhenomenonService)
    ac_vars = set()
    ac_opt_vars = set()
    for l_dict in laws.values():
        if l_dict["pheno"] == ac:
            ac_vars.update(l_dict["vars"])
            ac_opt_vars.update(l_dict["opt_vars"])
    
    fp_vars = set()
    if fp:
        for l_name, l_dict in laws.items():
            if any(l_name in vars_dict.get(v, {}).get("laws", []) for v in ac_vars):
                if l_dict["pheno"] == fp:
                    fp_vars.update(l_dict["vars"])
    
    mt_vars = set()
    for l_name, l_dict in laws.items():
        if any(l_name in vars_dict.get(v, {}).get("laws", []) for v in ac_opt_vars):
            if l_dict["pheno"] in mts:
                mt_vars.update(l_dict["vars"])

    me_vars = set()
    for l_name, l_dict in laws.items():
        if any(l_name in vars_dict.get(v, {}).get("laws", []) for v in mt_vars):
            if l_dict["pheno"] in mes:
                me_vars.update(l_dict["vars"])

    assoc_gas_vars = set()
    assoc_sld_vars = set()
    for l_name, l_dict in laws.items():
        for ac_opt_var in ac_opt_vars:
            if l_name in vars_dict.get(ac_opt_var, {}).get("laws", []):
                if l_dict["pheno"] in mts:
                    agl = l_dict.get("assoc_gas_law")
                    if agl and agl in laws and gass:
                        assoc_gas_vars.update(laws[agl]["vars"])
                    asl = l_dict.get("assoc_sld_law")
                    if asl and asl in laws and slds:
                        assoc_sld_vars.update(laws[asl]["vars"])

    param_law_vars = set()
    for l_name in param_law.values():
        if l_name in laws:
            param_law_vars.update(laws[l_name]["vars"])
    
    rxn_var_dict = {r: set() for r in rxn_dict}
    for r, r_phenos in rxn_dict.items():
        pheno_list = _normalize_list(r_phenos)
        for l_name, l_dict in laws.items():
            if l_dict["pheno"] in pheno_list:
                for v in l_dict["vars"]:
                    rxn_var_dict[r].add(v)
                    for v_law in vars_dict.get(v, {}).get("laws", []):
                        if v_law in laws:
                            rxn_var_dict[r].update(laws[v_law]["vars"])

    # Collect all active desc_vars
    desc_vars = set()
    desc_vars.update(ac_vars)
    desc_vars.update(fp_vars)
    desc_vars.update(mt_vars)
    desc_vars.update(me_vars)
    desc_vars.update(assoc_gas_vars)
    desc_vars.update(assoc_sld_vars)
    desc_vars.update(param_law_vars)
    for r_vars in rxn_var_dict.values():
        desc_vars.update(r_vars)

    parameters = []

    def add_param(category, name, gas=None, stm=None, rxn=None, spc=None):
        vd = vars_dict.get(name)
        if not vd: return
        
        # Determine Display Name & Units
        sym = vd.get("sym") or name
        unit_name = vd.get("unit")
        unit_sym = units_dict.get(unit_name, {}).get("sym") if unit_name else None
        
        # Build Label
        parts = [sym]
        if gas: parts.append(gas)
        if stm: parts.append(f"({stm})")
        if rxn: parts.append(f"[{rxn}]")
        if spc: parts.append(spc)
        label = " - ".join(parts)
        
        # Stable ID
        pid = f"{category}_{name}_{gas}_{stm}_{rxn}_{spc}".lower().replace(" ", "_").replace("+", "plus").replace(">", "to")
        
        parameters.append({
            "id": pid,
            "category": category,
            "name": name,
            "display_name": sym,
            "index": {
                "gas_or_solid": gas,
                "stream": stm,
                "reaction": rxn,
                "species": spc
            },
            "full_index": [name, gas, stm, rxn, spc],
            "label": label,
            "value": vd.get("val"),
            "unit": unit_sym or unit_name,
            "type": vd.get("cls")
        })

    # 2. Iterate and build parameters (Mapping logic from PhenomenonService)
    for v_name in sorted(desc_vars):
        vd = vars_dict.get(v_name, {})
        if not vd or vd.get("laws"): continue # Skip intermediate variables
        
        v_cls = vd.get("cls")
        v_dims = set(vd.get("dims", []))

        # st: StructureParameter, dims: []
        if v_cls == "StructureParameter" and not v_dims:
            add_param("st", v_name)
        
        # spc: PhysicsParameter, dims: ["Species"]
        elif v_cls == "PhysicsParameter" and v_dims == {"Species"}:
            for s in spcs: add_param("spc", v_name, spc=s)
            
        # stm: PhysicsParameter, dims: ["Stream"]
        elif v_cls == "PhysicsParameter" and v_dims == {"Stream"}:
            for st in stms: add_param("stm", v_name, stm=st)

        # gas: PhysicsParameter, dims: ["Gas"]
        elif v_cls == "PhysicsParameter" and v_dims == {"Gas"}:
            for g in gass: add_param("gas", v_name, gas=g)

        # sld: PhysicsParameter, dims: ["Solid"]
        elif v_cls == "PhysicsParameter" and v_dims == {"Solid"}:
            for s in slds: add_param("sld", v_name, gas=s)

        # mt/me: MassTransportParameter / PhysicsParameter with Gas/Stream/Species or Solid/Stream/Species
        elif v_cls in ["MassTransportParameter", "PhysicsParameter"]:
            if v_dims == {"Gas", "Stream", "Species"}:
                for g in gass:
                    for st in stms:
                        # Find species in this gas context (basic.gas[g].spc)
                        g_spcs = _normalize_list(basic.get("gas", {}).get(g, {}).get("spc"))
                        for s in g_spcs:
                            cat = "mt" if v_cls == "MassTransportParameter" else "me"
                            add_param(cat, v_name, gas=g, stm=st, spc=s)
            elif v_dims == {"Solid", "Stream", "Species"}:
                for sld in slds:
                    for st in stms:
                        s_spcs = _normalize_list(basic.get("sld", {}).get(sld, {}).get("spc"))
                        for s in s_spcs:
                            cat = "mt" if v_cls == "MassTransportParameter" else "me"
                            add_param(cat, v_name, gas=sld, stm=st, spc=s)
            elif not v_dims and v_cls == "MassTransportParameter":
                add_param("mt", v_name)

        # rxn: ReactionParameter, dims: ["Reaction", "Stream"] or ["Reaction"] or ["Reaction", "Species"]
        if v_cls == "ReactionParameter":
            for r in rxn_dict:
                if v_name in rxn_var_dict.get(r, set()):
                    if "Stream" in v_dims:
                        for st in stms: add_param("rxn", v_name, stm=st, rxn=r)
                    elif "Species" in v_dims:
                        if v_name == "Stoichiometric_Coefficient":
                            continue
                        lhs = r.split(" > ")[0]
                        lhs_spcs = [s.split(" ")[-1].strip() for s in lhs.split(" + ")]
                        for spc in lhs_spcs:
                            add_param("rxn", v_name, rxn=r, spc=spc)
                    else:
                        add_param("rxn", v_name, rxn=r)

    return {"parameters": parameters}


def query_species_roles(client: GraphDBClient) -> List[str]:
    """Return a sorted list of SpeciesRole names from the knowledge graph.

    Mirrors Flask GraphdbHandler.query_role, but uses SPARQLWrapper JSON via GraphDBClient.
    """
    sparql = (
        f"{PREFIX}"
        "select ?r where {"
        "?r rdf:type ontomo:SpeciesRole. "
        "}"
    )
    res = client.select(sparql)
    roles: List[str] = []
    for b in res.get("results", {}).get("bindings", []):
        uri = b.get("r", {}).get("value")
        name = _local(uri)
        if name:
            roles.append(name)
    return sorted(set(roles))
