from __future__ import annotations

from typing import Dict, Any

from ..services.graphdb import GraphDBClient

# RDF prefixes and class lists replicated from the Flask config for parity.
# Keeping FastAPI independent by co-locating required constants.
PREFIX_RDF = "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>"
# Note: If ontology path changes, update this URL accordingly.
PREFIX_ONTOMO = (
    "PREFIX ontomo: <https://raw.githubusercontent.com/"
    "sustainable-processes/KG4DT/refs/heads/dev-alkyne-hydrogenation/ontology/OntoMo.owl#>"
)
SPARQL_PREFIX = "\n".join([PREFIX_RDF, PREFIX_ONTOMO, ""])  # trailing newline for convenience

# Classes used in queries (kept for completeness; not strictly needed for /var and /unit)
MODEL_VARIABLE_CLASSES = [
    "Constant",
    "RateVariable",
    "StateVariable",
    "FlowParameter",
    "PhysicsParameter",
    "ReactionParameter",
    "OperationParameter",
    "StructureParameter",
    "MassTransportParameter",
]


def _clean_xml_mathml(s: str | None) -> str | None:
    """Normalize serialized XML/MathML strings similar to Flask utils behavior."""
    if s is None:
        return None
    # strip surrounding quotes if present
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        s = s[1:-1]
    # remove xmlns attributes to match frontend expectations
    s = s.replace(" xmlns=\"http://www.w3.org/1998/Math/MathML\"", "")
    return s


def query_var(client: GraphDBClient) -> Dict[str, Any]:
    """Query Model Variables from GraphDB and return a dict identical to Flask output.

    Output schema:
      {<var_name>: {cls, sym, val, unit, dims:[], laws:[]}, ...}
    """
    var_dict: Dict[str, Any] = {}

    for var_class in MODEL_VARIABLE_CLASSES:
        sparql = (
            f"{SPARQL_PREFIX}"
            "select ?v ?s ?u ?d ?l ?val where {"
            f"?v rdf:type ontomo:{var_class}. "
            f"?v ontomo:hasSymbol ?s. "
            f"optional{{?v ontomo:hasValue ?val}}. "
            f"optional{{?v ontomo:hasUnit ?u}}. "
            f"optional{{?v ontomo:hasDimension ?d}}. "
            f"optional{{?v ontomo:hasLaw ?l}}. "
            "}"
        )
        data = client.select(sparql)
        # SPARQLWrapper JSON format: { "results": { "bindings": [ {"v": {"type": ..., "value": ...}, ... }, ... ]}}
        for b in data.get("results", {}).get("bindings", []):
            v_uri = b.get("v", {}).get("value")
            s_val = b.get("s", {}).get("value")
            u_uri = b.get("u", {}).get("value")
            d_uri = b.get("d", {}).get("value")
            l_uri = b.get("l", {}).get("value")
            val_raw = b.get("val", {}).get("value")

            # extract local name after '#'
            def local(x: str | None) -> str | None:
                if not x:
                    return None
                return x.split("#")[-1]

            v = local(v_uri)
            if not v:
                continue
            u = local(u_uri)
            d = local(d_uri)
            l = local(l_uri)

            s_clean = _clean_xml_mathml(s_val)
            # Dimension label processing: remove trailing _<something>
            if d:
                parts = d.split("_")
                if len(parts) > 1:
                    d = " ".join(parts[:-1])

            # value conversion
            try:
                val = float(val_raw) if val_raw not in (None, "") else None
            except Exception:
                val = None

            if v not in var_dict:
                var_dict[v] = {
                    "cls": var_class,
                    "sym": None,
                    "val": None,
                    "unit": None,
                    "dims": [],
                    "laws": [],
                }
            var_dict[v]["sym"] = s_clean
            if val is not None:
                var_dict[v]["val"] = val
            if u:
                var_dict[v]["unit"] = u
            if d and d not in var_dict[v]["dims"]:
                var_dict[v]["dims"].append(d)
            if l and l not in var_dict[v]["laws"]:
                var_dict[v]["laws"].append(l)

    # sort keys and list values to match Flask response order
    out = {k: var_dict[k] for k in sorted(var_dict.keys())}
    for v in out.values():
        v["dims"] = sorted(v["dims"]) if isinstance(v.get("dims"), list) else []
        v["laws"] = sorted(v["laws"]) if isinstance(v.get("laws"), list) else []
    return out


def query_unit(client: GraphDBClient) -> Dict[str, Any]:
    """Query Units from GraphDB and return a dict identical to Flask output.

    Output schema:
      {<unit_name>: {cls: "Unit", sym, metr, rto, intcpt}, ...}
    """
    unit_dict: Dict[str, Any] = {}
    sparql = (
        f"{SPARQL_PREFIX}"
        "select ?u ?s ?m ?r ?i where {"
        f"?u rdf:type ontomo:Unit. "
        f"optional{{?u ontomo:hasSymbol ?s}}. "
        f"optional{{?u ontomo:hasMetric ?m}}. "
        f"optional{{?u ontomo:hasRatio ?r}}. "
        f"optional{{?u ontomo:hasIntercept ?i}}. "
        "}"
    )
    data = client.select(sparql)
    for b in data.get("results", {}).get("bindings", []):
        u_uri = b.get("u", {}).get("value")
        s_val = b.get("s", {}).get("value")
        m_uri = b.get("m", {}).get("value")
        r_raw = b.get("r", {}).get("value")
        i_raw = b.get("i", {}).get("value")

        def local(x: str | None) -> str | None:
            if not x:
                return None
            return x.split("#")[-1]

        u = local(u_uri)
        if not u:
            continue
        m = local(m_uri)
        s_clean = _clean_xml_mathml(s_val)

        try:
            rto = float(r_raw) if r_raw not in (None, "") else None
        except Exception:
            rto = None
        try:
            intcpt = float(i_raw) if i_raw not in (None, "") else None
        except Exception:
            intcpt = None

        if u not in unit_dict:
            unit_dict[u] = {"cls": "Unit", "sym": None, "metr": None, "rto": None, "intcpt": None}
        unit_dict[u]["sym"] = s_clean
        if m:
            unit_dict[u]["metr"] = m
        if rto is not None:
            unit_dict[u]["rto"] = rto
        if intcpt is not None:
            unit_dict[u]["intcpt"] = intcpt

    out = {k: unit_dict[k] for k in sorted(unit_dict.keys())}
    return out
