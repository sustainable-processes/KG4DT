from __future__ import annotations

from typing import Any, Dict, List, Optional

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
    return {
        "error": "NotImplemented",
        "detail": "query_pheno is not migrated yet. Implement SPARQLs to assemble the full phenomenon dictionary.",
    }


def query_fp_by_ac(client: GraphDBClient, ac: str) -> Dict[str, Any]:
    return {
        "error": "NotImplemented",
        "detail": f"Flow patterns for accumulation '{ac}' not implemented yet in FastAPI.",
    }


def query_mt_by_fp(client: GraphDBClient, fp: str) -> Dict[str, Any]:
    return {
        "error": "NotImplemented",
        "detail": f"Mass transport phenomena for flow pattern '{fp}' not implemented yet in FastAPI.",
    }


def query_me_by_mt(client: GraphDBClient, mt: str) -> List[str] | Dict[str, Any]:
    return {
        "error": "NotImplemented",
        "detail": f"Mass equilibrium phenomena for mass transport '{mt}' not implemented yet in FastAPI.",
    }


def query_param_law(client: GraphDBClient, desc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "error": "NotImplemented",
        "detail": "Parameter-to-law mapping not implemented yet in FastAPI.",
        "input": desc,
    }


def query_rxn(client: GraphDBClient, filters: Optional[Dict[str, Any]] = None) -> Any:
    return {
        "error": "NotImplemented",
        "detail": "Reaction phenomenon query not implemented yet in FastAPI.",
        "filters": filters or {},
    }
