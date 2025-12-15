from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Set

from ..services.graphdb import GraphDBClient

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
    """Return minimal law metadata required for param_law computation.

    Output: { law_name: {"pheno": <phenomenon or None>, "vars": set([...])} }
    """
    laws: Dict[str, Dict[str, Any]] = {}
    sparql = (
        f"{PREFIX}"
        "select ?l ?v ?p where {"
        "?l rdf:type ontomo:Law. "
        "?l ontomo:hasModelVariable ?v. "
        "optional{?l ontomo:isAssociatedWith ?p}. "
        "}"
    )
    data = client.select(sparql)
    for b in data.get("results", {}).get("bindings", []):
        l = _local(b.get("l", {}).get("value"))
        v = _local(b.get("v", {}).get("value"))
        p = _local(b.get("p", {}).get("value"))
        if not l or not v:
            continue
        if l not in laws:
            laws[l] = {"pheno": p, "vars": set()}
        laws[l]["vars"].add(v)
        if p is not None and laws[l]["pheno"] is None:
            laws[l]["pheno"] = p
    # convert sets to lists
    for k in list(laws.keys()):
        laws[k]["vars"] = sorted(list(laws[k]["vars"]))
    return laws


def _normalize_list(val: Any) -> List[str]:
    if val is None:
        return []
    if isinstance(val, list):
        return [str(x).strip() for x in val if x is not None and str(x).strip() != ""]
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
    from .graphdb_model_utils import query_var as _query_var

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


def query_info(client: GraphDBClient, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return a minimal information block similar to Flask /api/model/info.

    Currently returns:
      - pheno: full phenomena dictionary
      - rxn: list of ReactionPhenomenon names
    The context parameter is accepted for parity and future use.
    """
    try:
        pheno = query_pheno(client)
    except Exception:
        pheno = {}
    try:
        rxn = query_rxn(client)
    except Exception:
        rxn = []
    return {
        "pheno": pheno,
        "rxn": rxn,
    }


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
