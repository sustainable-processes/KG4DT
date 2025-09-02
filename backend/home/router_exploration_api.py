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




@blueprint.route("/api/model/simulation", methods=["POST"])
def api_model_simulation_tabular():
    """
    Run simulation for a table of experiments and return tabular results.

    Request JSON body:
    {
      "model_context": { ... },                         # required
      "operation_keys": [[...], ...],                   # required; list of keys (each key is a list) for parameter_value_dict
      "operation_columns": ["OP1", "OP2", ...],      # required; columns in each row mapped to operation_keys order
      "rows": [
        {"experiment_no": 1, "OP1": 300, "OP2": 1.0, ...},
        ...
      ],                                                 # required
      "result_columns": ["A", "B", ...]               # optional; defaults to species list from model_context.basic.species
    }

    Response (200):
    {
      "rows": [
        {"experiment_no": 1, "OP1": 300, "OP2": 1.0, "A": 0.12, "B": 0.34, ...},
        ...
      ],
      "species": ["A", "B", ...]
    }
    """
    try:
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return jsonify({"error": "Invalid JSON body; expected an object."}), 400

        model_context = payload.get("model_context")
        op_keys = payload.get("operation_keys") or payload.get("data_key")
        op_cols = payload.get("operation_columns") or payload.get("data_columns")
        rows = payload.get("rows")
        result_cols = payload.get("result_columns")

        if not model_context or not isinstance(model_context, dict):
            return jsonify({"error": "Field 'model_context' is required and must be an object."}), 400
        if not op_keys or not isinstance(op_keys, list):
            return jsonify({"error": "Field 'operation_keys' is required and must be a list."}), 400
        if not op_cols or not isinstance(op_cols, list):
            return jsonify({"error": "Field 'operation_columns' is required and must be a list."}), 400
        if not rows or not isinstance(rows, list):
            return jsonify({"error": "Field 'rows' is required and must be a list of records."}), 400
        if len(op_keys) != len(op_cols):
            return jsonify({"error": "Length of 'operation_keys' must match length of 'operation_columns'."}), 400

        # Determine species/result columns
        species = (model_context.get("basic", {}) or {}).get("species") or []
        if not result_cols:
            result_cols = list(species)
        if not isinstance(result_cols, list) or not result_cols:
            return jsonify({"error": "'result_columns' must be a non-empty list or omitted to use species."}), 400

        # Build request for ModelSimulationAgent
        data_values = []
        exp_nos = []
        for r in rows:
            if not isinstance(r, dict):
                return jsonify({"error": "Each item in 'rows' must be an object."}), 400
            exp_no = r.get("experiment_no")
            if exp_no is None:
                exp_no = r.get("experiment")
            exp_nos.append(exp_no)
            try:
                vals = [r[c] for c in op_cols]
            except KeyError as e:
                return jsonify({"error": f"Missing operation column in row: {str(e)}"}), 400
            data_values.append(vals)

        sim_req = {
            "model_context": model_context,
            "parameter": {"key": [], "value": []},
            "data": {"key": op_keys, "value": data_values},
        }

        # Run simulation
        entity = g.graphdb_handler.query()
        agent = ModelSimulationAgent(entity, sim_req)
        sim_results = agent.simulate_scipy() or []

        # Helper: extract final average values per species from one experiment result list
        def extract_final_averages(result_list, expected_species):
            # result_list: list of dicts with keys 'data' and 'label'
            # labels we want: "average  <species>"
            final_map = {}
            for item in (result_list or []):
                label = item.get("label")
                if not isinstance(label, str):
                    continue
                if not label.startswith("average"):
                    continue
                # expected format: "average  <species>"
                parts = label.split()
                sp = parts[-1] if parts else None
                series = item.get("data") or []
                if series:
                    final_val = series[-1][1]
                    final_map[sp] = final_val
            # Return values in order of expected_species
            return [final_map.get(sp) for sp in expected_species]

        # Build response rows
        out_rows = []
        # Align expected species order with result_cols if provided differently
        expected_species = result_cols
        if not expected_species:
            expected_species = species
        for idx, r in enumerate(rows):
            avg_vals = extract_final_averages(sim_results[idx] if idx < len(sim_results) else [], expected_species)
            merged = {"experiment_no": exp_nos[idx]}
            # include OP columns back
            for c in op_cols:
                merged[c] = r.get(c)
            # include result columns
            for c, v in zip(expected_species, avg_vals):
                merged[c] = v
            out_rows.append(merged)

        return jsonify({"rows": out_rows, "species": expected_species}), 200

    except Exception as e:
        return jsonify({
            "error": "Internal server error while running simulation.",
            "detail": str(e)
        }), 500


@blueprint.route("/api/model/calibration", methods=["POST"])
def api_model_calibration_tabular():
    """
    Run calibration using a table of experiments where some result columns may be missing.
    The calibration fills missing values by optimizing parameters, and returns rows with completed results.

    Request JSON body:
    {
      "model_context": { ... },                         # required
      "parameter": {"key": [...], "init": [...], "min": [...], "max": [...]},  # required
      "operation_keys": [[...], ...],                   # required
      "operation_columns": ["OP1", "OP2", ...],      # required
      "rows": [ {"experiment_no": 1, "OP1": 300, ..., "A": 0.1, "B": null}, ... ],  # required
      "result_columns": ["A", "B", ...]               # optional; defaults to species list
    }

    Response (200):
    {
      "parameter": {"key": [...], "value": [...]},
      "rmse": <float>,
      "rows": [ {"experiment_no": 1, "OP1": ..., "A": <filled>, "B": <filled>, ...}, ... ]
    }
    """
    try:
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return jsonify({"error": "Invalid JSON body; expected an object."}), 400

        model_context = payload.get("model_context")
        param_block = payload.get("parameter")
        op_keys = payload.get("operation_keys") or payload.get("data_key")
        op_cols = payload.get("operation_columns") or payload.get("data_columns")
        rows = payload.get("rows")
        result_cols = payload.get("result_columns")

        if not model_context or not isinstance(model_context, dict):
            return jsonify({"error": "Field 'model_context' is required and must be an object."}), 400
        if not isinstance(param_block, dict) or not all(k in param_block for k in ("key", "init", "min", "max")):
            return jsonify({"error": "Field 'parameter' must include 'key', 'init', 'min', 'max'."}), 400
        if not op_keys or not isinstance(op_keys, list):
            return jsonify({"error": "Field 'operation_keys' is required and must be a list."}), 400
        if not op_cols or not isinstance(op_cols, list):
            return jsonify({"error": "Field 'operation_columns' is required and must be a list."}), 400
        if not rows or not isinstance(rows, list):
            return jsonify({"error": "Field 'rows' is required and must be a list of records."}), 400
        if len(op_keys) != len(op_cols):
            return jsonify({"error": "Length of 'operation_keys' must match length of 'operation_columns'."}), 400

        species = (model_context.get("basic", {}) or {}).get("species") or []
        if not result_cols:
            result_cols = list(species)
        if not isinstance(result_cols, list) or not result_cols:
            return jsonify({"error": "'result_columns' must be a non-empty list or omitted to use species."}), 400

        # Build data.value: concatenate operation values then result values (aligned with result_cols/species order)
        data_values = []
        exp_nos = []
        for r in rows:
            if not isinstance(r, dict):
                return jsonify({"error": "Each item in 'rows' must be an object."}), 400
            exp_no = r.get("experiment_no")
            if exp_no is None:
                exp_no = r.get("experiment")
            exp_nos.append(exp_no)
            try:
                op_vals = [r[c] for c in op_cols]
            except KeyError as e:
                return jsonify({"error": f"Missing operation column in row: {str(e)}"}), 400
            # results provided in row (may be missing)
            res_vals = [r.get(c) for c in result_cols]
            data_values.append(op_vals + res_vals)

        calib_req = {
            "model_context": model_context,
            "parameter": param_block,
            "data": {"key": op_keys, "value": data_values},
        }

        # Run calibration
        entity = g.graphdb_handler.query()
        agent = ModelCalibrationAgent(entity, calib_req)
        result = agent.calibration_scipy()
        if not result:
            return jsonify({"error": "Calibration failed or returned no result."}), 500

        # Extract final averages from returned simulation results similar to simulation route
        sim_results = result.get("simulation") or []
        def extract_final_averages(result_list, expected_species):
            final_map = {}
            for item in (result_list or []):
                label = item.get("label")
                if not isinstance(label, str):
                    continue
                if not label.startswith("average"):
                    continue
                parts = label.split()
                sp = parts[-1] if parts else None
                series = item.get("data") or []
                if series:
                    final_val = series[-1][1]
                    final_map[sp] = final_val
            return [final_map.get(sp) for sp in expected_species]

        expected_species = result_cols
        out_rows = []
        for idx, r in enumerate(rows):
            avg_vals = extract_final_averages(sim_results[idx] if idx < len(sim_results) else [], expected_species)
            merged = {"experiment_no": exp_nos[idx]}
            for c in op_cols:
                merged[c] = r.get(c)
            for c, v in zip(expected_species, avg_vals):
                merged[c] = v
            out_rows.append(merged)

        response = {
            "parameter": result.get("parameter"),
            "rmse": result.get("rmse"),
            "rows": out_rows
        }
        return jsonify(response), 200

    except Exception as e:
        return jsonify({
            "error": "Internal server error while running calibration.",
            "detail": str(e)
        }), 500
