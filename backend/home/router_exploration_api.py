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


@blueprint.route("/api/model/sym", methods=["GET"])
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

        sym = g.graphdb_handler.query_symbol(unit)
        if sym is None or sym == "":
            return jsonify({
                "error": "No symbol found for the specified unit.",
                "unit": unit
            }), 404

        return jsonify({"sym": sym}), 200

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



@blueprint.route("/api/model/op_param", methods=["POST"])
def api_model_operation_parameter():
    """
    POST body JSON may contain keys: {"basic", "desc"}
    The "basic" value may contain keys: {"spc", "rxn", "stm", "gas", "sld"}.
    The "desc" value may contain keys: {"ac", "fp", "mt", "me", "rxn", "param_law" }.
    Returns operation parameters with dimensions of species and stream/solid/gas.
    Response example: {"op_param": [
        ("Stirring_Speed", None, None), 
        ("Initial_Concentration", "H2O", "Stream 1"), 
        ...
    ]}
    - Returns 400 if no filters provided.
    - Returns 404 if no parameters found for the given filters.
    """
    try:
        # TODO: preload check Jonathan
        context = request.get_json(silent=True) or {}
        # if not isinstance(payload, dict):
        #     return jsonify({"error": "Invalid JSON body; expected an object."}), 400

        # keys = ("ac", "fp", "mt", "me", "rxn", "param_law")
        # filters = {k: payload.get(k) for k in keys if k in payload}

        # if not any(filters.get(k) for k in keys):
        #     return jsonify({
        #         "error": "Provide at least one of 'ac', 'fp', 'mt', 'me', 'rxn', or 'param_law' in the JSON body.",
        #         "hint": {"example": {"fp": "Annular_Microflow", "param_law": ["Arrhenius"]}}
        #     }), 400

        op_params = g.graphdb_handler.query_op_param(context) or set()
        if not op_params:
            return jsonify({
                "error": "No Operation/Structure parameters found for the specified filters.",
                "context": context
            }), 404

        return jsonify({"op_param": list(op_params)}), 200

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
      "operation_columns": ["OP1", "OP2", ...],         # required; columns in each row to send as inputs
      "rows": [
        {"experiment_no": 1, "OP1": 300, "OP2": 1.0, ...},
        ...
      ],                                                # required
      "result_columns": ["A", "B", ...]                 # required; which species/results to extract
      // "operation_keys": [[...], ...]                 # optional; if omitted, defaults to [[col] for col in operation_columns]
    }

    Response (200):
    {
      "rows": [
        {"experiment_no": 1, "OP1": 300, "OP2": 1.0, "A": 0.12, "B": 0.34, ...},
        ...
      ]
    }
    """
    try:
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return jsonify({"error": "Invalid JSON body; expected an object."}), 400

        model_context = payload.get("model_context")
        op_cols = payload.get("operation_columns") or payload.get("data_columns")
        rows = payload.get("rows")
        result_cols = payload.get("result_columns")
        # operation_keys is optional now; if missing, derive from operation_columns
        op_keys = payload.get("operation_keys") or payload.get("data_key")

        if not model_context or not isinstance(model_context, dict):
            return jsonify({"error": "Field 'model_context' is required and must be an object."}), 400
        if not op_cols or not isinstance(op_cols, list):
            return jsonify({"error": "Field 'operation_columns' is required and must be a list."}), 400
        if not rows or not isinstance(rows, list):
            return jsonify({"error": "Field 'rows' is required and must be a list of records."}), 400
        if not result_cols or not isinstance(result_cols, list):
            return jsonify({"error": "Field 'result_columns' is required and must be a non-empty list."}), 400

        # If operation_keys not provided, use a 1:1 mapping with column names
        if not op_keys:
            op_keys = [[c] for c in op_cols]
        if not isinstance(op_keys, list) or len(op_keys) != len(op_cols):
            return jsonify({"error": "Length of 'operation_keys' must match length of 'operation_columns'."}), 400

        # Build request for ModelSimulationAgent
        data_values = []
        exp_nos = []
        for r in rows:
            if not isinstance(r, dict):
                return jsonify({"error": "Each item in 'rows' must be an object."}), 400
            exp_no = r.get("experiment_no", r.get("experiment"))
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
                parts = label.split()
                sp = parts[-1] if parts else None
                series = item.get("data") or []
                if series:
                    final_val = series[-1][1]
                    final_map[sp] = final_val
            return [final_map.get(sp) for sp in expected_species]

        # Build response rows
        out_rows = []
        expected_species = result_cols
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

        # New response format: just the list of rows
        return jsonify(out_rows), 200

    except Exception as e:
        return jsonify({
            "error": "Internal server error while running simulation.",
            "detail": str(e)
        }), 500


@blueprint.route("/api/model/calibration", methods=["POST"])
def api_model_calibration_tabular():
    """
    Run calibration using a table of experiments where some result columns may be missing.
    Accepts a simplified JSON and returns optimized parameter mapping.

    Request JSON body:
    {
      "model_context": { ... },                         # required
      "parameter": {"key": ["param1", ...], "min": [...], "max": [...]},  # required; 'init' optional
      "operation_columns": ["OP1", "OP2", ...],         # required
      "rows": [
        {"experiment_no": 1, "OP1": 300, ..., "A": 0.1, "B": null},
        {"experiment_no": 2, "OP1": 300, ..., "A": 0.2, "B": null}
      ],                                                # required
      "result_columns": ["A", "B", ...]                 # required
      // "operation_keys": [[...], ...]                 # optional; defaults to [[col] for col in operation_columns]
      // "parameter": may include "init": [...]         # optional; will be derived from min/max if omitted
    }

    Response (200):
    {
      "param1": 1,
      "param2": 2,
      "param3": 3
    }
    """
    try:
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return jsonify({"error": "Invalid JSON body; expected an object."}), 400

        model_context = payload.get("model_context")
        param_block = payload.get("parameter") or {}
        op_cols = payload.get("operation_columns") or payload.get("data_columns")
        rows = payload.get("rows")
        result_cols = payload.get("result_columns")
        # operation_keys optional; if missing, map 1:1 to operation_columns
        op_keys = payload.get("operation_keys") or payload.get("data_key")

        if not model_context or not isinstance(model_context, dict):
            return jsonify({"error": "Field 'model_context' is required and must be an object."}), 400
        if not isinstance(param_block, dict) or not all(k in param_block for k in ("key", "min", "max")):
            return jsonify({"error": "Field 'parameter' must include 'key', 'min', and 'max' arrays."}), 400
        if not op_cols or not isinstance(op_cols, list):
            return jsonify({"error": "Field 'operation_columns' is required and must be a list."}), 400
        if not rows or not isinstance(rows, list):
            return jsonify({"error": "Field 'rows' is required and must be a list of records."}), 400
        if not result_cols or not isinstance(result_cols, list):
            return jsonify({"error": "Field 'result_columns' is required and must be a non-empty list."}), 400

        # Ensure parameter arrays have consistent lengths; derive 'init' if missing
        p_keys = param_block.get("key") or []
        p_min = param_block.get("min") or []
        p_max = param_block.get("max") or []
        if not (isinstance(p_keys, list) and isinstance(p_min, list) and isinstance(p_max, list)):
            return jsonify({"error": "Parameter 'key', 'min', and 'max' must be lists."}), 400
        if not (len(p_keys) == len(p_min) == len(p_max)):
            return jsonify({"error": "Parameter 'key', 'min', and 'max' must have the same length."}), 400

        p_init = param_block.get("init")
        if not p_init:
            # Derive init as midpoint of min/max when numeric; otherwise use min
            derived_init = []
            for lo, hi in zip(p_min, p_max):
                try:
                    if lo is not None and hi is not None:
                        derived_init.append((float(lo) + float(hi)) / 2.0)
                    else:
                        derived_init.append(float(lo) if lo is not None else 0.0)
                except Exception:
                    derived_init.append(lo if lo is not None else 0.0)
            param_block["init"] = derived_init
        else:
            if not isinstance(p_init, list) or len(p_init) != len(p_keys):
                return jsonify({"error": "Parameter 'init' must be a list with the same length as 'key'."}), 400

        # If operation_keys not provided, use a 1:1 mapping with column names
        if not op_keys:
            op_keys = [[c] for c in op_cols]
        if not isinstance(op_keys, list) or len(op_keys) != len(op_cols):
            return jsonify({"error": "Length of 'operation_keys' must match length of 'operation_columns'."}), 400

        # Build data.value: concatenate operation values then result values (aligned with result_cols)
        data_values = []
        for r in rows:
            if not isinstance(r, dict):
                return jsonify({"error": "Each item in 'rows' must be an object."}), 400
            try:
                op_vals = [r[c] for c in op_cols]
            except KeyError as e:
                return jsonify({"error": f"Missing operation column in row: {str(e)}"}), 400
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

        # Expect result format: {"parameter": {"key": [...], "value": [...]}, ...}
        param_out = result.get("parameter") or {}
        keys_out = param_out.get("key") or p_keys
        vals_out = param_out.get("value")
        if not isinstance(vals_out, list) or len(keys_out) != len(vals_out):
            return jsonify({"error": "Calibration returned invalid parameter results."}), 500

        # Build simple mapping { "param": value, ... }
        mapping = {k: v for k, v in zip(keys_out, vals_out)}
        return jsonify(mapping), 200

    except Exception as e:
        return jsonify({
            "error": "Internal server error while running calibration.",
            "detail": str(e)
        }), 500

