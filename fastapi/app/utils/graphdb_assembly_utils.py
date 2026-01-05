from __future__ import annotations

from typing import Any, Dict, List

from ..services.graphdb import GraphDBClient
from .graphdb_model_utils import SPARQL_PREFIX, _clean_xml_mathml


def _local_name(uri: str | None) -> str | None:
    if not uri:
        return None
    return uri.split("#")[-1]


def query_context_template(client: GraphDBClient) -> Dict[str, Any]:
    """Query context templates from GraphDB.

    Mirrors Flask's GraphdbHandler.query_context_template output shape for parity.

    Returns a dict like:
      {
        "<contextname>": {
          "accumulation": <str>,
          "structure": {
            "<descriptor>": {
              "default": <float|bool>,
              "min": <float>,
              "max": <float>,
              "options": [<str>, ...],
              "default_option": <str>,
              "unit": <str>,
              "unit_symbol": <str>,
            },
            ...
          },
          "operation": { ... }
        },
        ...
      }
    """

    ctx: Dict[str, Any] = {}

    # 1) Contexts and their sections/phenomenon
    sparql1 = (
        f"{SPARQL_PREFIX}"
        "select ?c ?p ?ss ?os ?type where {"
        "?c rdf:type ontomo:Context. "
        "filter(!contains(str(?c), \"_Operation\") && !contains(str(?c), \"_Structure\"))"
        "optional{?c rdf:type ?type. filter(?type IN (ontomo:ReactorContext, ontomo:UtilityContext, ontomo:ProcessStreamContext))}"
        "optional{?c ontomo:hasPhenomenon ?p. }"
        "optional{?c ontomo:hasStructureSection ?ss. }"
        "optional{?c ontomo:hasOperationSection ?os. }"
        "}"
    )
    data1 = client.select(sparql1)
    for b in data1.get("results", {}).get("bindings", []):
        c_uri = b.get("c", {}).get("value")
        p_uri = b.get("p", {}).get("value")
        ss_uri = b.get("ss", {}).get("value")
        os_uri = b.get("os", {}).get("value")

        c_local = _local_name(c_uri)
        if not c_local:
            continue
        
        # Consistent filtering: skip if it's explicitly a section naming pattern
        if "_Operation" in c_local or "_Structure" in c_local:
            continue

        c_name = c_local.replace("_Context", "").lower()

        if c_name not in ctx:
            ctx[c_name] = {}

        p_local = _local_name(p_uri)
        ss_local = _local_name(ss_uri)
        os_local = _local_name(os_uri)

        if p_local:
            ctx[c_name]["accumulation"] = p_local.lower()
        if ss_local and "structure" not in ctx[c_name]:
            ctx[c_name]["structure"] = {}
        if os_local and "operation" not in ctx[c_name]:
            ctx[c_name]["operation"] = {}

    # 2) Structure section descriptors
    sparql2 = (
        f"{SPARQL_PREFIX}"
        "select ?c ?s ?d ?v ?lb ?ub ?o ?do ?u ?us where {"
        "?c rdf:type ontomo:Context. "
        "filter(!contains(str(?c), \"_Operation\") && !contains(str(?c), \"_Structure\"))"
        "?s rdf:type ontomo:ContextSection. "
        "?c ontomo:hasStructureSection ?s. "
        "?d rdf:type ontomo:Descriptor. "
        "?s ontomo:hasDescriptor ?d. "
        "optional{?d ontomo:hasDefaultValue ?v.} "
        "optional{?d ontomo:hasLowerBound ?lb.} "
        "optional{?d ontomo:hasUpperBound ?ub.} "
        "optional{?d ontomo:hasOption ?o.} "
        "optional{?d ontomo:hasDefaultOption ?do.} "
        "optional{?d ontomo:hasUnit ?u. ?u ontomo:hasSymbol ?us. filter(bound(?u) && bound(?us))}"
        "}"
    )
    data2 = client.select(sparql2)
    for b in data2.get("results", {}).get("bindings", []):
        c_uri = b.get("c", {}).get("value")
        d_uri = b.get("d", {}).get("value")
        v_raw = b.get("v", {}).get("value")
        lb_raw = b.get("lb", {}).get("value")
        ub_raw = b.get("ub", {}).get("value")
        o_raw = b.get("o", {}).get("value")
        do_raw = b.get("do", {}).get("value")
        u_uri = b.get("u", {}).get("value")
        us_raw = b.get("us", {}).get("value")

        c_local = _local_name(c_uri)
        if not c_local:
            continue
        c_name = c_local.replace("_Context", "").lower()
        # ensure context and structure map
        if c_name not in ctx:
            ctx[c_name] = {}
        if "structure" not in ctx[c_name]:
            ctx[c_name]["structure"] = {}

        d_local = _local_name(d_uri)
        if not d_local:
            continue
        d_local = d_local.lower()

        entry = ctx[c_name]["structure"].setdefault(d_local, {})

        if v_raw:
            if v_raw == "true":
                entry["default"] = True
            else:
                try:
                    entry["default"] = float(v_raw)
                except Exception:
                    entry["default"] = v_raw
                entry["value"] = 0
        elif lb_raw and ub_raw:
            try:
                entry["min"] = float(lb_raw)
                entry["max"] = float(ub_raw)
            except Exception:
                pass
        elif o_raw:
            entry.setdefault("options", [])
            opt = _local_name(o_raw) or o_raw
            entry["options"].append(opt.lower())
        else:
            entry["value"] = 0

        if do_raw:
            entry["default_option"] = (_local_name(do_raw) or do_raw).lower()

        u_local = _local_name(u_uri)
        if u_local:
            entry["unit"] = u_local.lower()
        if us_raw:
            entry["unit_symbol"] = _clean_xml_mathml(us_raw).lower()

    # 3) Operation section descriptors
    sparql3 = (
        f"{SPARQL_PREFIX}"
        "select ?c ?s ?d ?v ?lb ?ub ?o ?do ?u ?us where {"
        "?c rdf:type ontomo:Context. "
        "filter(!contains(str(?c), \"_Operation\") && !contains(str(?c), \"_Structure\"))"
        "?s rdf:type ontomo:ContextSection. "
        "?c ontomo:hasOperationSection ?s. "
        "?d rdf:type ontomo:Descriptor. "
        "?s ontomo:hasDescriptor ?d. "
        "optional{?d ontomo:hasDefaultValue ?v.} "
        "optional{?d ontomo:hasLowerBound ?lb.} "
        "optional{?d ontomo:hasUpperBound ?ub.} "
        "optional{?d ontomo:hasOption ?o.} "
        "optional{?d ontomo:hasDefaultOption ?do.} "
        "optional{?d ontomo:hasUnit ?u. ?u ontomo:hasSymbol ?us. filter(bound(?u) && bound(?us))}"
        "}"
    )
    data3 = client.select(sparql3)
    for b in data3.get("results", {}).get("bindings", []):
        c_uri = b.get("c", {}).get("value")
        d_uri = b.get("d", {}).get("value")
        v_raw = b.get("v", {}).get("value")
        lb_raw = b.get("lb", {}).get("value")
        ub_raw = b.get("ub", {}).get("value")
        o_raw = b.get("o", {}).get("value")
        do_raw = b.get("do", {}).get("value")
        u_uri = b.get("u", {}).get("value")
        us_raw = b.get("us", {}).get("value")

        c_local = _local_name(c_uri)
        if not c_local:
            continue
        c_name = c_local.replace("_Context", "").lower()
        # ensure context and operation map
        if c_name not in ctx:
            ctx[c_name] = {}
        if "operation" not in ctx[c_name]:
            ctx[c_name]["operation"] = {}

        d_local = _local_name(d_uri)
        if not d_local:
            continue
        d_local = d_local.lower()

        entry = ctx[c_name]["operation"].setdefault(d_local, {})

        if v_raw:
            if v_raw == "true":
                entry["default"] = True
            else:
                try:
                    entry["default"] = float(v_raw)
                except Exception:
                    entry["default"] = v_raw
                entry["value"] = 0
        elif lb_raw and ub_raw:
            try:
                entry["min"] = float(lb_raw)
                entry["max"] = float(ub_raw)
            except Exception:
                pass
        elif o_raw:
            entry.setdefault("options", [])
            opt = _local_name(o_raw) or o_raw
            entry["options"].append(opt.lower())
        else:
            entry["value"] = 0

        if do_raw:
            entry["default_option"] = (_local_name(do_raw) or do_raw).lower()

        u_local = _local_name(u_uri)
        if u_local:
            entry["unit"] = u_local.lower()
        if us_raw:
            entry["unit_symbol"] = _clean_xml_mathml(us_raw).lower()

    # Sorting to mimic Flask behavior
    out: Dict[str, Any] = {k: ctx[k] for k in sorted(ctx.keys())}
    for c_name, cval in out.items():
        # At this level, keys include: accumulation (str), structure (dict), operation (dict)
        for k in list(cval.keys()):
            v = cval[k]
            if isinstance(v, list):
                cval[k] = sorted(v)
            elif isinstance(v, dict):
                cval[k] = {dk: v[dk] for dk in sorted(v.keys())}
            # else leave primitives as-is
    return out


def list_context_template_names(client: GraphDBClient) -> List[str]:
    """List available context template names only (sorted ascending).

    Names are derived from Context individuals with the "_Context" suffix removed,
    matching Flask naming (e.g., "Gas_Context" -> "Gas").
    """
    # Only list Context individuals and exclude any whose IRI contains
    # section-like suffixes to avoid returning entries such as
    # *_Operation or *_Structure.
    sparql = (
        f"{SPARQL_PREFIX}"
        "select ?c where { "
        "?c rdf:type ontomo:Context. "
        "filter(!contains(str(?c), \"_Operation\") && !contains(str(?c), \"_Structure\"))"
        " }"
    )
    data = client.select(sparql)
    names: List[str] = []
    seen: set[str] = set()
    for b in data.get("results", {}).get("bindings", []):
        c_uri = b.get("c", {}).get("value")
        c_local = _local_name(c_uri)
        if not c_local:
            continue
        name = c_local.replace("_Context", "")
        # Defensive filter in case the backend returns any section-like names
        if "_Operation" in name or "_Structure" in name:
            continue
        if name not in seen:
            seen.add(name)
            names.append(name)
    return sorted(names)


def list_context_templates_with_icons(client: GraphDBClient) -> Dict[str, str | None]:
    """List context template names with their icon value/URL (if any).

    - Excludes section-like entries (e.g., *_Operation_Section, *_Structure_Section).
    - Strips the trailing "_Context" from local names (e.g., Gas_Context -> Gas).
    - Returns a mapping: { name: icon_value_or_url_or_identifier }.

    Resolution priority (highest to lowest):
      1) ontomo:hasIcon/ontomo:hasValue (e.g., "Solid")
      2) ontomo:hasIcon/ontomo:hasURL (e.g., "https://.../icon.svg")
      3) ontomo:hasIcon (IRI of the icon individual)
    """
    sparql = (
        f"{SPARQL_PREFIX}"
        "select ?c ?icon ?iconUrl ?iconValue where { "
        "?c rdf:type ontomo:Context. "
        "filter(!contains(str(?c), \"_Operation\") && !contains(str(?c), \"_Structure\"))"
        # Keep the icon resource and any attached data properties
        "optional{ ?c ontomo:hasIcon ?icon. }"
        "optional{ ?c ontomo:hasIcon/ontomo:hasURL ?iconUrl. }"
        "optional{ ?c ontomo:hasIcon/ontomo:hasValue ?iconValue. }"
        " }"
    )
    data = client.select(sparql)
    result: Dict[str, str | None] = {}
    for b in data.get("results", {}).get("bindings", []):
        c_uri = b.get("c", {}).get("value")
        icon_val = b.get("icon", {}).get("value")
        icon_url_val = b.get("iconUrl", {}).get("value")
        icon_value_val = b.get("iconValue", {}).get("value")

        print(f"{c_uri=} {icon_val=} {icon_url_val=} {icon_value_val=}")

        c_local = _local_name(c_uri)
        if not c_local:
            continue
        name = c_local.replace("_Context", "")
        # Defensive filter as well
        if "_Operation" in name or "_Structure" in name:
            continue
        # Initialize entry if first time we see this name
        if name not in result:
            result[name] = None
        # Prefer explicit literal value, then URL, then resource IRI
        if icon_value_val:
            result[name] = icon_value_val
        elif icon_url_val:
            result[name] = icon_url_val
        elif icon_val:
            result[name] = icon_val
    print(f"{result=}")
    return result


__all__ = [
    "query_context_template",
    "list_context_template_names",
    "list_context_templates_with_icons",
]
