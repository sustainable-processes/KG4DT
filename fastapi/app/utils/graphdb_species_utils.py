from __future__ import annotations

from typing import Dict, List, Optional

from ..services.graphdb import GraphDBClient
from .graphdb_exploration_utils import PREFIX, _local


def query_species_roles_with_attribute(client: GraphDBClient) -> List[Dict[str, Optional[str]]]:
    """Return a sorted list of SpeciesRole with optional attribute from the knowledge graph.

    Attempts multiple likely predicates for the attribute and picks the first available:
    - ontomo:hasAttribute
    - ontomo:hasRoleAttribute
    - ontomo:attribute

    Output format (sorted ascending by name):
      [
        {"name": <role_name>, "attribute": <attr_or_None>},
        ...
      ]
    """
    sparql = (
        f"{PREFIX}"
        "select ?r ?attrOut where {"
        "?r rdf:type ontomo:SpeciesRole. "
        "optional{?r ontomo:hasAttribute ?attr1}. "
        "optional{?r ontomo:hasRoleAttribute ?attr2}. "
        "optional{?r ontomo:attribute ?attr3}. "
        "BIND(COALESCE(?attr1, ?attr2, ?attr3) AS ?attrOut) "
        "}"
    )
    res = client.select(sparql)
    # Deduplicate by role name, prefer first non-null attribute encountered
    tmp: Dict[str, Optional[str]] = {}
    for b in res.get("results", {}).get("bindings", []):
        r_uri = b.get("r", {}).get("value")
        name = _local(r_uri)
        if not name:
            continue
        attr_val = b.get("attrOut", {}).get("value") if b.get("attrOut") else None
        attr_local = _local(attr_val) if attr_val else None
        if name not in tmp:
            tmp[name] = attr_local
        else:
            if tmp[name] is None and attr_local is not None:
                tmp[name] = attr_local

    items = [{"name": n, "attribute": tmp[n]} for n in sorted(tmp.keys())]
    return items
