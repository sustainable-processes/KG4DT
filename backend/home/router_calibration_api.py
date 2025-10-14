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
    """Resolve the symbols for one or more Unit individuals.

    Request examples:
      - POST body: {"unit": "Pa"}
      - POST body: {"units": ["Pa", "m", "s"]}
      - GET with JSON body: {"units": ["Pa", "m"]}
      - GET with query params (fallback): /api/model/symbol?unit=Pa&unit=m or /api/model/symbol?unit=Pa,m

    Response examples:
      - {"symbols": {"Pa": "<math>...Pa...</math>"}}
      - {"symbols": {"Pa": "<math>...Pa...</math>", "m": "<math>...m...</math>", "s": null}, "not_found": ["s"]}
    """
    try:
        payload = request.get_json(silent=True) or {}

        units = []

        def _add(val):
            if val is None:
                return
            if isinstance(val, list):
                for x in val:
                    _add(x)
            else:
                s = str(val).strip()
                if s:
                    units.append(s)

        # Prefer JSON body
        if isinstance(payload, dict):
            if "units" in payload:
                _add(payload.get("units"))
            if "unit" in payload:
                _add(payload.get("unit"))

        # Fallback to query params when body is empty or fields missing
        if not units:
            lst = request.args.getlist("unit")
            if not lst:
                lst = request.args.getlist("units")
            if not lst:
                s = request.args.get("unit") or request.args.get("units")
                if s:
                    lst = [p.strip() for p in s.split(",") if p.strip()]
            _add(lst)

        # Deduplicate while preserving order
        seen = set()
        uniq_units = []
        for u in units:
            if u not in seen:
                seen.add(u)
                uniq_units.append(u)

        if not uniq_units:
            return jsonify({
                "error": "No 'unit' or 'units' provided.",
                "hint": {"POST": {"units": ["Pa", "m"]}}
            }), 400

        symbols = {}
        not_found = []
        for u in uniq_units:
            try:
                sym = g.graphdb_handler.query_symbol(u)
            except Exception:
                sym = None
            if sym:
                symbols[u] = sym
            else:
                symbols[u] = None
                not_found.append(u)

        if len(not_found) == len(uniq_units):
            return jsonify({
                "error": "No symbols found for the requested unit(s).",
                "units": uniq_units
            }), 404

        resp = {"symbols": symbols}
        if not_found:
            resp["not_found"] = not_found
        return jsonify(resp), 200

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




@blueprint.route("/api/model/op_param", methods=["GET"])
def api_model_operation_parameter():
    """
    Retrieve candidate Operation Parameters (OPs) for a modeling context.

    What this endpoint does:
    - Given a modeling context (basic entities like streams/gases/solids/species and selected
      phenomena like accumulation/flow-pattern/mass-transfer/mass-equilibrium/reaction), it
      derives which OperationParameter variables are required or applicable, and at what index
      (global, per-stream, per-gas, per-solid, or per-species within those).

    Request (GET with JSON body only):
    Body can be either the full context object or wrapped with a top-level key "context".
    {
      "context": {            // optional wrapper
        "basic": {            // optional (but recommended when OPs depend on indices)
          "stm": {"S1": {"spc": ["A", "B"]}},
          "gas": {"G1": {"spc": ["O2"]}},
          "sld": {"Cat": {"spc": ["Cat"]}}
        },
        "desc": {            // at least one selector recommended
          "ac": "Batch",
          "fp": "Well_Mixed",
          "mt": ["Gas_Liquid_Mass_Transfer"],
          "me": ["Gas_Dissolution_Equilibrium"],
          "rxn": {"R1": ["Arrhenius"]},
          "param_law": {"k_La": "Annular_Microflow_Correlation"}
        }
      }
    }

    Response (200):
    {
      "op_param": [[name, index1, index2], ...],
      "count": <int>
    }
    Example: {"op_param": [["Stirring_Speed", null, null], ["Initial_Concentration", "S1", "A"]], "count": 2}

    Errors:
    - 400: invalid/missing JSON or invalid shapes for basic/desc.
    - 404: no operation parameters could be derived for the given context.
    """
    try:
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return jsonify({"error": "Invalid JSON body; expected an object."}), 400

        # Normalize and validate shapes with minimal assumptions
        basic = payload.get("basic") or {}
        desc = payload.get("desc") or {}

        if not isinstance(basic, dict) or not isinstance(desc, dict):
            return jsonify({
                "error": "Fields 'basic' and 'desc' (when provided) must be objects.",
                "hint": {"basic": {"stm": {"S1": {"spc": ["A"]}}}, "desc": {"fp": "Well_Mixed"}}
            }), 400

        def _ensure_dict(d):
            return d if isinstance(d, dict) else {}

        def _ensure_idx_map(m):
            # Expect mapping like {"S1": {"spc": ["A", "B"]}}
            if not isinstance(m, dict):
                return {}
            out = {}
            for k, v in m.items():
                if not isinstance(v, dict):
                    continue
                spc = v.get("spc")
                if spc is None:
                    # allow empty list if not specified
                    out[k] = {"spc": []}
                elif isinstance(spc, list):
                    out[k] = {"spc": [str(x).strip() for x in spc if x is not None and str(x).strip() != ""]}
                else:
                    # coerce single value to list
                    s = str(spc).strip()
                    out[k] = {"spc": [s] if s else []}
            return out

        basic_norm = {
            "stm": _ensure_idx_map(_ensure_dict(basic.get("stm"))),
            "gas": _ensure_idx_map(_ensure_dict(basic.get("gas"))),
            "sld": _ensure_idx_map(_ensure_dict(basic.get("sld")))
        }

        # species list at the top-level (rarely used here) may be provided; keep if a list of strings
        if isinstance(basic.get("spc"), list):
            basic_norm["spc"] = [str(x).strip() for x in basic.get("spc") if x is not None and str(x).strip()]
        else:
            if "spc" in basic_norm:
                basic_norm.pop("spc", None)

        def _norm_str(x):
            return str(x).strip() if isinstance(x, (str, int, float)) else None

        def _norm_list(val):
            if val is None:
                return []
            if isinstance(val, list):
                items = val
            else:
                items = [val]
            out = []
            for x in items:
                s = _norm_str(x)
                if s:
                    out.append(s)
            return out

        # desc normalization
        desc_norm = {
            "ac": _norm_str(desc.get("ac")),
            "fp": _norm_str(desc.get("fp")),
            "mt": _norm_list(desc.get("mt")),
            "me": _norm_list(desc.get("me")),
            # rxn: {"R1": ["Pheno1", "Pheno2"]}
            "rxn": {},
            # param_law: {param: law}
            "param_law": {}
        }

        # rxn normalization: allow list of pairs [[rxn, pheno], ...] or mapping
        rxn = desc.get("rxn")
        if isinstance(rxn, dict):
            for rk, rv in rxn.items():
                lst = _norm_list(rv)
                if lst:
                    desc_norm["rxn"][str(rk).strip()] = lst
        elif isinstance(rxn, list):
            for item in rxn:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    r = _norm_str(item[0])
                    ph = _norm_str(item[1])
                    if r and ph:
                        desc_norm["rxn"].setdefault(r, []).append(ph)
        elif isinstance(rxn, (str, int, float)):
            # single reaction name with no phenos: keep but empty list
            r = _norm_str(rxn)
            if r:
                desc_norm["rxn"][r] = []

        # param_law normalization: allow list of {p: l} or a single mapping
        pl = desc.get("param_law")
        if isinstance(pl, dict):
            for pk, pv in pl.items():
                ps = _norm_str(pk)
                ls = _norm_str(pv)
                if ps and ls:
                    desc_norm["param_law"][ps] = ls
        elif isinstance(pl, list):
            for item in pl:
                if isinstance(item, dict):
                    for pk, pv in item.items():
                        ps = _norm_str(pk)
                        ls = _norm_str(pv)
                        if ps and ls:
                            desc_norm["param_law"][ps] = ls

        # If desc is entirely empty, inform user (encourage filters for meaningful results)
        if not (desc_norm["ac"] or desc_norm["fp"] or desc_norm["mt"] or desc_norm["me"] or desc_norm["rxn"] or desc_norm["param_law"]):
            return jsonify({
                "error": "Provide at least one descriptor in 'desc' (ac, fp, mt, me, rxn, or param_law).",
                "hint": {"desc": {"fp": "Well_Mixed", "mt": ["Gas_Liquid_Mass_Transfer"]}}
            }), 400

        normalized_context = {"basic": basic_norm, "desc": desc_norm}

        # Delegate to handler
        raw = g.graphdb_handler.query_op_param(normalized_context) or {}

        # Accept dict-of-keys or set-of-tuples; convert to a stable, JSON-friendly list
        if isinstance(raw, dict):
            keys = list(raw.keys())
        elif isinstance(raw, (set, list, tuple)):
            keys = list(raw)
        else:
            keys = []

        # Ensure all items are 5-tuples and JSON-serializable
        out = []
        for k in keys:
            try:
                name, idx1, idx2, idx3, idx4 = k if isinstance(k, (list, tuple)) else (k, None, None, None, None)
            except Exception:
                continue
            out.append([name, idx1, idx2, idx3, idx4])

        if not out:
            return jsonify({
                "error": "No operation parameters derived for the specified context.",
                "context": normalized_context
            }), 404

        # Sort for deterministic output
        out.sort(key=lambda x: (
            str(x[0]), 
            str(x[1]) if x[1] is not None else "", 
            str(x[2]) if x[2] is not None else "",
            str(x[3]) if x[3] is not None else "",
            str(x[4]) if x[4] is not None else ""
        ))
        return jsonify({"op_param": out, "count": len(out)}), 200

    except Exception as e:
        return jsonify({
            "error": "Internal server error while processing the request.",
            "detail": str(e)
        }), 500



@blueprint.route("/api/model/simulate", methods=["GET"])
def api_model_simulate():
    """
    Run simulation for a table of experiments and return tabular results.

    Best-practice enhancements:
    - Require application/json Content-Type.
    - Validate request shape strictly.
    - Support both 'val' and 'value' for data rows (backward compatible).
    - Convert OP indices to tuples for internal processing.
    """
    try:
        if not request.is_json:
            return jsonify({"error": "Unsupported Media Type. Use Content-Type: application/json."}), 415

        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return jsonify({"error": "Invalid JSON body; expected an object."}), 400

        context = payload.get("context")
        op_params = payload.get("op_params")
        if not isinstance(context, dict):
            return jsonify({"error": "Field 'context' is required and must be an object."}), 400
        if not isinstance(op_params, dict):
            return jsonify({"error": "Field 'op_params' is required and must be an object."}), 400

        # Normalize op_params: support both 'val' and 'value'
        norm_op = _normalize_dataset_section("op_params", op_params)
        if isinstance(norm_op, tuple):  # (error_json, status)
            return norm_op

        sim_req = {
            "context": context,
            "op_params": norm_op,
        }

        # Run simulation
        entity = g.graphdb_handler.query()
        sim_agent = ModelSimulationAgent(entity, sim_req)
        sim_res = sim_agent.simulate_scipy()

        return jsonify(sim_res), 200

    except Exception as e:
        return jsonify({
            "error": "Internal server error while running simulation.",
            "detail": str(e)
        }), 500


@blueprint.route("/api/model/cal_param", methods=["GET"])
def api_model_calibration_parameter():
    """
    Retrieve candidate calibration parameters (reaction/mass-transfer) for a modeling context.

    Best-practice enhancements:
    - Require application/json Content-Type.
    - Accept either full context at top-level or in a top-level 'context' field.
    - Normalize shapes consistent with /api/model/op_param.
    - Clear 400/404 errors with hints.
    - Ensure deterministic, JSON-friendly output (lists, sorted).
    """
    try:
        if not request.is_json:
            return jsonify({"error": "Unsupported Media Type. Use Content-Type: application/json."}), 415

        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return jsonify({"error": "Invalid JSON body; expected an object."}), 400

        context_in = payload.get("context") if "context" in payload else payload
        if not isinstance(context_in, dict):
            return jsonify({"error": "Field 'context' must be an object when provided."}), 400

        normalized_context = _normalize_context(context_in)
        desc_norm = normalized_context.get("desc", {})
        if _desc_is_empty(desc_norm):
            return jsonify({
                "error": "Provide at least one descriptor in 'desc' (ac, fp, mt, me, rxn, or param_law).",
                "hint": {"desc": {"fp": "Well_Mixed", "mt": ["Gas_Liquid_Mass_Transfer"]}}
            }), 400

        cal_params = g.graphdb_handler.query_cal_param(normalized_context) or set()
        if not cal_params:
            return jsonify({
                "error": "No Reaction/MassTransport parameters found for the specified filters.",
                "context": normalized_context
            }), 404

        # Convert to a deterministic, JSON-serializable list of lists
        def _as_list(x):
            return list(x) if isinstance(x, (list, tuple)) else x
        out = [ _as_list(x) for x in cal_params ]
        try:
            out.sort(key=lambda x: tuple(str(i) for i in x))
        except Exception:
            pass

        return jsonify({"cal_param": out, "count": len(out)}), 200

    except Exception as e:
        return jsonify({
            "error": "Internal server error while processing the request.",
            "detail": str(e)
        }), 500


@blueprint.route("/api/model/calibrate", methods=["GET"])
def api_model_calibrate():
    """
    Run calibration using a table of experiments with possibly missing result columns.

    Best-practice enhancements:
    - Require application/json Content-Type.
    - Validate and normalize shapes.
    - Support both 'val' and 'value' for dataset arrays (backward compatible).
    - Ensure bounds pairs for 'cal_params'.
    """
    try:
        if not request.is_json:
            return jsonify({"error": "Unsupported Media Type. Use Content-Type: application/json."}), 415

        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return jsonify({"error": "Invalid JSON body; expected an object."}), 400

        context = payload.get("context")
        op_params_in = payload.get("op_params")
        reals_in = payload.get("reals")
        cal_params_in = payload.get("cal_params")

        if not isinstance(context, dict):
            return jsonify({"error": "Field 'context' is required and must be an object."}), 400
        if not isinstance(op_params_in, dict):
            return jsonify({"error": "Field 'op_params' is required and must be an object."}), 400
        if not isinstance(reals_in, dict):
            return jsonify({"error": "Field 'reals' is required and must be an object."}), 400
        if not isinstance(cal_params_in, dict):
            return jsonify({"error": "Field 'cal_params' is required and must be an object."}), 400

        # Normalize sections
        op_params = _normalize_dataset_section("op_params", op_params_in)
        if isinstance(op_params, tuple):
            return op_params
        reals = _normalize_dataset_section("reals", reals_in)
        if isinstance(reals, tuple):
            return reals
        cal_params = _normalize_bounds_section("cal_params", cal_params_in)
        if isinstance(cal_params, tuple):
            return cal_params

        cal_req = {
            "context": context,
            "op_params": op_params,
            "reals": reals,
            "cal_params": cal_params,
        }

        # Run calibration
        entity = g.graphdb_handler.query()
        cal_agent = ModelCalibrationAgent(entity, cal_req)
        cal_res = cal_agent.calibrate_scipy()

        return jsonify(cal_res), 200

    except Exception as e:
        return jsonify({
            "error": "Internal server error while running calibration.",
            "detail": str(e)
        }), 500



# ----------------------
# Helper utilities (request validation/normalization)
# ----------------------

def _json_error(message, status=400, detail=None, hint=None):
    payload = {"error": message}
    if detail is not None:
        payload["detail"] = detail
    if hint is not None:
        payload["hint"] = hint
    return jsonify(payload), status


def _normalize_dataset_section(name, section):
    """Normalize a dataset-like section with keys: {"ind": [...], "val"|"value": [[...], ...]}.
    - Ensures indices are tuples for internal processing.
    - Validates that each row has the same number of elements as indices length.
    Returns a normalized dict or (json_error, status) tuple on error.
    """
    if not isinstance(section, dict):
        return _json_error(f"Field '{name}' must be an object with 'ind' and 'val' fields.", 400)

    inds = section.get("ind")
    vals = section.get("val")
    if vals is None and "value" in section:
        vals = section.get("value")

    if not isinstance(inds, list) or not all(isinstance(x, (list, tuple)) for x in inds):
        return _json_error(f"Field '{name}.ind' must be a list of index tuples/lists.", 400)
    if not isinstance(vals, list) or not all(isinstance(row, list) for row in vals):
        return _json_error(f"Field '{name}.val' must be a list of rows (lists).", 400,
                           hint={name: {"ind": [["Name", None, None, None, None]], "val": [[1.0]]}})

    n_cols = len(inds)
    for i, row in enumerate(vals):
        if len(row) != n_cols:
            return _json_error(
                f"Row {i} in '{name}.val' has length {len(row)} but expected {n_cols} per '{name}.ind'.",
                400
            )

    return {"ind": [tuple(ind) for ind in inds], "val": vals}


def _normalize_bounds_section(name, section):
    """Normalize a bounds-like section with keys: {"ind": [...], "val": [[lo, hi], ...]}.
    Returns normalized dict or (json_error, status) on error.
    """
    if not isinstance(section, dict):
        return _json_error(f"Field '{name}' must be an object with 'ind' and 'val' fields.", 400)

    inds = section.get("ind")
    vals = section.get("val")
    if vals is None and "value" in section:
        vals = section.get("value")

    if not isinstance(inds, list) or not all(isinstance(x, (list, tuple)) for x in inds):
        return _json_error(f"Field '{name}.ind' must be a list of index tuples/lists.", 400)
    if not isinstance(vals, list) or not all(isinstance(b, (list, tuple)) and len(b) == 2 for b in vals):
        return _json_error(f"Field '{name}.val' must be a list of [lo, hi] pairs.", 400,
                           hint={name: {"ind": [["Activation_Energy", None, "S1", "R1", None]], "val": [[0.0, 10.0]]}})
    if len(vals) != len(inds):
        return _json_error(
            f"'{name}.val' must have the same length as '{name}.ind' (got {len(vals)} vs {len(inds)}).",
            400
        )

    return {"ind": [tuple(ind) for ind in inds], "val": [list(b) for b in vals]}


def _normalize_context(context):
    """Normalize modeling context into a stable structure used by graphdb handler.
    Accepts a dict possibly with keys 'basic' and 'desc'.
    Returns a dict {"basic": {...}, "desc": {...}}.
    """
    def _ensure_dict(d):
        return d if isinstance(d, dict) else {}

    def _ensure_idx_map(m):
        if not isinstance(m, dict):
            return {}
        out = {}
        for k, v in m.items():
            if not isinstance(v, dict):
                continue
            spc = v.get("spc")
            if spc is None:
                out[k] = {"spc": []}
            elif isinstance(spc, list):
                out[k] = {"spc": [str(x).strip() for x in spc if x is not None and str(x).strip() != ""]}
            else:
                s = str(spc).strip()
                out[k] = {"spc": [s] if s else []}
        return out

    def _norm_str(x):
        return str(x).strip() if isinstance(x, (str, int, float)) else None

    def _norm_list(val):
        if val is None:
            return []
        if isinstance(val, list):
            items = val
        else:
            items = [val]
        out = []
        for x in items:
            s = _norm_str(x)
            if s:
                out.append(s)
        return out

    basic = _ensure_dict(context.get("basic"))
    desc = _ensure_dict(context.get("desc"))

    basic_norm = {
        "stm": _ensure_idx_map(_ensure_dict(basic.get("stm"))),
        "gas": _ensure_idx_map(_ensure_dict(basic.get("gas"))),
        "sld": _ensure_idx_map(_ensure_dict(basic.get("sld"))),
    }
    if isinstance(basic.get("spc"), list):
        basic_norm["spc"] = [str(x).strip() for x in basic.get("spc") if x is not None and str(x).strip()]

    desc_norm = {
        "ac": _norm_str(desc.get("ac")),
        "fp": _norm_str(desc.get("fp")),
        "mt": _norm_list(desc.get("mt")),
        "me": _norm_list(desc.get("me")),
        "rxn": {},
        "param_law": {},
    }

    rxn = desc.get("rxn")
    if isinstance(rxn, dict):
        for rk, rv in rxn.items():
            lst = _norm_list(rv)
            if lst:
                desc_norm["rxn"][str(rk).strip()] = lst
    elif isinstance(rxn, list):
        for item in rxn:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                r = _norm_str(item[0])
                ph = _norm_str(item[1])
                if r and ph:
                    desc_norm["rxn"].setdefault(r, []).append(ph)
    elif isinstance(rxn, (str, int, float)):
        r = _norm_str(rxn)
        if r:
            desc_norm["rxn"][r] = []

    pl = desc.get("param_law")
    if isinstance(pl, dict):
        for pk, pv in pl.items():
            ps = _norm_str(pk)
            ls = _norm_str(pv)
            if ps and ls:
                desc_norm["param_law"][ps] = ls
    elif isinstance(pl, list):
        for item in pl:
            if isinstance(item, dict):
                for pk, pv in item.items():
                    ps = _norm_str(pk)
                    ls = _norm_str(pv)
                    if ps and ls:
                        desc_norm["param_law"][ps] = ls

    return {"basic": basic_norm, "desc": desc_norm}


def _desc_is_empty(desc_norm):
    return not (desc_norm.get("ac") or desc_norm.get("fp") or desc_norm.get("mt") or desc_norm.get("me") or desc_norm.get("rxn") or desc_norm.get("param_law"))
