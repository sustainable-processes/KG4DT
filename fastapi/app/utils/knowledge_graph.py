from __future__ import annotations

from typing import Any, Dict, List, Tuple


def law2label(law: str) -> str:
    """Convert an ontology law name into a multi-line human label.

    Examples:
        >>> law2label("Mass_transfer_with_convection_by_Newton")
        'Mass transfer\nconvection\nby Newton'
    """
    if "by" in law:
        return (
            law.split("_with_")[0].replace("_", " ")
            + "\n"
            + law.split("_with_")[1].split("_by_")[0].replace("_", " ")
            + "\nby "
            + law.split("_by_")[1].replace("_", " ")
        )
    else:
        return (
            law.split("_with_")[0].replace("_", " ")
            + "\n"
            + law.split("_with_")[1].split("_by_")[0].replace("_", " ")
        )


def to_knowledge_graph_data(entity: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Build nodes/edges for the Knowledge Graph visualization from an entity dict.

    This mirrors the logic used in the Flask implementation (ModelKnowledgeGraphAgent)
    but is provided as a standalone functional utility for FastAPI.

    Expected input schema (subset):
        entity = {
            "model_variable": {
                <name>: {"laws": [<law>...], "definition": <definition>|None, ...},
                ...
            },
            "law": {
                <law>: {
                    "phenomenon": <str>,
                    "model_variables": [<name>...],
                    "optional_model_variables": [<name>...],
                    "differential_model_variable": <name>|None,
                },
                ...
            },
            "definition": {
                <definition>: {"model_variables": [<name>...]},
                ...
            },
        }

    Returns:
        { "node": [...], "edge": [...] }
    """

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    node2id: Dict[str, int] = {}
    node_id = 0
    edge_id = 0

    # Model variables as group 0
    for model_variable in entity.get("model_variable", {}):
        nodes.append({
            "id": node_id,
            "label": str(model_variable).replace("_", ""),
            "group": 0,
        })
        node2id[model_variable] = node_id
        node_id += 1

    # Laws as group 1
    for law in entity.get("law", {}):
        nodes.append({
            "id": node_id,
            "label": law2label(str(law)),
            "group": 1,
        })
        node2id[law] = node_id
        node_id += 1

    # Definitions as group 1
    for definition in entity.get("definition", {}):
        nodes.append({
            "id": node_id,
            "label": str(definition).replace("_", ""),
            "group": 1,
        })
        node2id[definition] = node_id
        node_id += 1

    # Edges: model_variable -> law(s) and -> definition
    for model_variable, vdata in entity.get("model_variable", {}).items():
        for law in vdata.get("laws", []) or []:
            if model_variable in node2id and law in node2id:
                edges.append({
                    "id": edge_id,
                    "from": node2id[model_variable],
                    "to": node2id[law],
                    "label": "hasLaw",
                    "arrows": "to",
                    "color": {"inherit": "from"},
                })
                edge_id += 1

        definition = vdata.get("definition")
        if definition and model_variable in node2id and definition in node2id:
            edges.append({
                "id": edge_id,
                "from": node2id[model_variable],
                "to": node2id[definition],
                "label": "hasDefinition",
                "arrows": "to",
                "color": {"inherit": "from"},
            })
            edge_id += 1

    # Edges from laws to variables and special relationships
    for law, ldata in entity.get("law", {}).items():
        # Skip instantaneous phenomenon as per original logic
        if ldata.get("phenomenon") == "Instantaneous":
            continue

        for mv in ldata.get("model_variables", []) or []:
            if law in node2id and mv in node2id:
                edges.append({
                    "id": edge_id,
                    "from": node2id[law],
                    "to": node2id[mv],
                    "label": "hasModelVariable",
                    "arrows": "to",
                    "color": {"inherit": "from"},
                })
                edge_id += 1

        for mv in ldata.get("optional_model_variables", []) or []:
            if law in node2id and mv in node2id:
                edges.append({
                    "id": edge_id,
                    "from": node2id[law],
                    "to": node2id[mv],
                    "dashes": True,
                    "label": "hasOptionalModelVariable",
                    "arrows": "to",
                    "color": {"inherit": "from"},
                })
                edge_id += 1

        dmv = ldata.get("differential_model_variable")
        if dmv and law in node2id and dmv in node2id:
            edges.append({
                "id": edge_id,
                "from": node2id[law],
                "to": node2id[dmv],
                "dashes": True,
                "label": "hasDifferentialModelVariable",
                "arrows": "to",
                "color": {"inherit": "from"},
            })
            edge_id += 1

    # Edges from definitions to variables
    for definition, ddata in entity.get("definition", {}).items():
        for mv in ddata.get("model_variables", []) or []:
            if definition in node2id and mv in node2id:
                edges.append({
                    "id": edge_id,
                    "from": node2id[definition],
                    "to": node2id[mv],
                    "label": "hasModelVariable",
                    "arrows": "to",
                    "color": {"inherit": "from"},
                })
                edge_id += 1

    return {"node": nodes, "edge": edges}


__all__ = ["law2label", "to_knowledge_graph_data"]
