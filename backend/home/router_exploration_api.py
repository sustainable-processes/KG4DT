import os
import json

from io import BytesIO
from pathlib import Path
from datetime import datetime
from flask import (
    g, jsonify, render_template, request, send_file,
    current_app
)
from . import blueprint
from ..utils.model_agent import ModelAgent
from ..utils.model_calibration_agent import ModelCalibrationAgent
from ..utils.model_exploration_agent import ModelExplorationAgent
from ..utils.model_simulation_agent import ModelSimulationAgent
from ..utils.model_knowledge_graph_agent import ModelKnowledgeGraphAgent
from ..utils.physical_property_agent import PhysicalPropertyAgent
from ..utils.solvent_miscibility_agent import SolventMiscibilityAgent

@blueprint.route("/api/model/law", methods=["GET"])
def api_model_law():
    entity = g.graphdb_handler.query_law(None)

    return jsonify(entity)


@blueprint.route("/api/model/symbol", methods=["GET"])
def api_model_symbol():
    """Return the symbol of a unit by its local name via SPARQL ontomo:hasSymbol.
    Example: /api/model/symbol?unit=Pa
    Response: {"unit": "Pa", "symbol": "<math>...<mtext>Pa</mtext>...</math>"}
    """
    try:
        unit = request.args.get("unit")
        if unit is None or str(unit).strip() == "":
            return jsonify({
                "error": "Missing required query parameter 'unit'.",
                "hint": "/api/model/symbol?unit=Pa"
            }), 400

        symbol = g.graphdb_handler.query_symbol(unit)
        if symbol is None or symbol == "":
            return jsonify({
                "error": "No symbol found for the specified unit.",
                "unit": unit
            }), 404

        return jsonify({"symbol": symbol}), 200

    except Exception as e:
        return jsonify({
            "error": "Internal server error while processing the request.",
            "detail": str(e)
        }), 500


@blueprint.route("/api/knowledge_graph/triplets", methods=["GET"])
def api_knowledge_graph_triplets():
    """Return knowledge graph in a simple triplets JSON structure.
    Response example:
    {
      "triplets": {
        "var": {"velocity": {}},
        "law": {"law1": {}},
        "relationship": [["velocity", "hasLaw", "law1"], ["law1", "hasModelVariable", "velocity"]]
      }
    }
    """
    try:
        entity = g.graphdb_handler.query()
        vars_map = entity.get("var", {}) or {}
        laws_map = entity.get("law", {}) or {}

        # Nodes (as empty objects per spec)
        var_nodes = {name: {} for name in sorted(vars_map.keys())}
        law_nodes = {name: {} for name in sorted(laws_map.keys())}

        # Relationships
        relationships = []
        seen = set()

        def add_rel(s, p, o):
            t = (s, p, o)
            if s and p and o and t not in seen:
                relationships.append([s, p, o])
                seen.add(t)

        # var -> hasLaw -> law (inverse of hasModelVariable)
        for v_name, v_meta in vars_map.items():
            for l_name in (v_meta.get("laws", []) or []):
                add_rel(v_name, "hasLaw", l_name)

        # law -> hasModelVariable -> var
        for l_name, l_meta in laws_map.items():
            for v_name in (l_meta.get("vars", []) or []):
                add_rel(l_name, "hasModelVariable", v_name)
            for v_name in (l_meta.get("opt_vars", []) or []):
                add_rel(l_name, "hasOptionalModelVariable", v_name)

        data = {
            "var": var_nodes,
            "law": law_nodes,
            "relationship": relationships,
        }
        return jsonify({"triplets": data}), 200

    except Exception as e:
        return jsonify({
            "error": "Internal server error while building knowledge graph triplets.",
            "detail": str(e)
        }), 500



@blueprint.route("/api/model/operation_parameter", methods=["POST"])
def api_model_operation_parameter():
    """
    POST body JSON may contain keys: { "ac", "fp", "mt", "me", "rxn", "param_law" }.
    Returns operation/structure parameter variable names connected via Laws that satisfy the filters.
    Response example: {"operation_parameter": ["Stirring_Speed", "Residence_Time", ...]}
    - Returns 400 if no filters provided.
    - Returns 404 if no parameters found for the given filters.
    """
    try:
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return jsonify({"error": "Invalid JSON body; expected an object."}), 400

        keys = ("ac", "fp", "mt", "me", "rxn", "param_law")
        filters = {k: payload.get(k) for k in keys if k in payload}

        if not any(filters.get(k) for k in keys):
            return jsonify({
                "error": "Provide at least one of 'ac', 'fp', 'mt', 'me', 'rxn', or 'param_law' in the JSON body.",
                "hint": {"example": {"fp": "Annular_Microflow", "param_law": ["Arrhenius"]}}
            }), 400

        result_set = g.graphdb_handler.query_operation_parameters(filters) or set()
        if not result_set:
            return jsonify({
                "error": "No Operation/Structure parameters found for the specified filters.",
                "filters": filters
            }), 404

        return jsonify({"operation_parameter": sorted(list(result_set))}), 200

    except Exception as e:
        return jsonify({
            "error": "Internal server error while processing the request.",
            "detail": str(e)
        }), 500
