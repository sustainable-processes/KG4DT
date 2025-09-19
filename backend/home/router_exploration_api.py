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

        # Accept either top-level context or body-as-context
        context = payload.get("context") if "context" in payload else payload
        if not isinstance(context, dict):
            return jsonify({"error": "Field 'context' must be an object when provided."}), 400

        # Normalize and validate shapes with minimal assumptions
        basic = context.get("basic") or {}
        desc = context.get("desc") or {}
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

        # Ensure all items are 3-tuples and JSON-serializable
        out = []
        for k in keys:
            try:
                name, idx1, idx2 = k if isinstance(k, (list, tuple)) else (k, None, None)
            except Exception:
                continue
            out.append([name, idx1, idx2])

        if not out:
            return jsonify({
                "error": "No operation parameters derived for the specified context.",
                "context": normalized_context
            }), 404

        # Sort for deterministic output
        out.sort(key=lambda x: (str(x[0]), str(x[1]) if x[1] is not None else "", str(x[2]) if x[2] is not None else ""))
        return jsonify({"op_param": out, "count": len(out)}), 200

    except Exception as e:
        return jsonify({
            "error": "Internal server error while processing the request.",
            "detail": str(e)
        }), 500



@blueprint.route("/api/model/simulate", methods=["GET", "POST"])
def api_model_simulate_tabular():
    """
    Run one or many simulations by supplying a modeling context and operation parameter values.

    What this endpoint does:
    - It accepts a model context plus a list of Operation Parameters (OPs) with indices
      and a matrix of values (one row per simulation run).
    - It builds the input expected by the ModelSimulationAgent and returns its results as-is.

    Request (GET/POST with JSON body only):
    {
      "context": { ... },
      "op_params": {
        "key": [[name, idx1, idx2], ...],   // OP identifiers (use /api/model/op_param to discover available keys)
        "value": [[v11, v12, ...],          // one row per simulation; each row length must equal len(key)
                   [v21, v22, ...],
                   ...]
        // also accepted: "values", "rows", "row", "val" as aliases for "value"
        // if a single flat list is provided, it will be treated as one row
      }
    }
    Notes on indices:
    - For global OPs: use [name, null, null]
    - For stream-indexed OPs: [name, stream, null]
    - For gas-/solid-indexed OPs: [name, gasOrSolid, null]
    - For species-within-stream/gas/solid OPs: [name, container, species]

    Response (200): agent-dependent list of simulation outputs.

    Errors:
    - 400: invalid/missing JSON, shape mismatches, or unknown indices.
    - 404: no simulations requested (empty value array).
    """
    try:
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return jsonify({"error": "Invalid JSON body; expected an object."}), 400

        # context is required (accept alias 'model_context' for convenience)
        context = payload.get("context") or payload.get("model_context")
        if not isinstance(context, dict):
            return jsonify({"error": "Field 'context' is required and must be an object."}), 400

        # op_params with 'key' and 'value' are required
        op_params = payload.get("op_params")
        if not isinstance(op_params, dict):
            return jsonify({"error": "Field 'op_params' is required and must be an object with 'key' and 'value'."}), 400

        keys = op_params.get("key")
        # Accept common aliases for the values matrix
        vals = op_params.get("value")
        if vals is None:
            for alias in ("values", "rows", "row", "val"):
                if alias in op_params:
                    vals = op_params.get(alias)
                    break
        if not isinstance(keys, list) or not keys:
            return jsonify({"error": "'op_params.key' must be a non-empty list of [name, idx1, idx2]."}), 400

        # If a single flat vector is provided, treat it as one row
        if isinstance(vals, list) and vals and all(not isinstance(x, (list, tuple)) for x in vals):
            vals = [vals]

        if not isinstance(vals, list) or not vals:
            return jsonify({
                "error": "'op_params.value' must be a non-empty list (each item is a row of values).",
                "hint": {
                    "shape": {"op_params": {"key": [["Batch_Time", None, None], ["Pressure", None, None]], "value": [[3600, 101325]]}},
                    "also_accepts": ["values", "rows", "row", "val"],
                    "note": "If you have a single row of values, send a flat list or wrap it as [[...]]."
                }
            }), 400

        # Basic indices present in context
        basic = (context.get("basic") or {}) if isinstance(context, dict) else {}
        stms = set((basic.get("stm") or {}).keys())
        gass = set((basic.get("gas") or {}).keys())
        slds = set((basic.get("sld") or {}).keys())

        def _norm_key(item):
            # Expect [name, idx1, idx2]
            if not isinstance(item, (list, tuple)):
                return None
            parts = list(item) + [None, None, None]  # ensure length >= 3
            name = str(parts[0]).strip() if parts[0] is not None else None
            idx1 = str(parts[1]).strip() if parts[1] is not None and str(parts[1]).strip() != "" else None
            idx2 = str(parts[2]).strip() if parts[2] is not None and str(parts[2]).strip() != "" else None
            if not name:
                return None
            return [name, idx1, idx2]

        norm_keys = []
        for i, k in enumerate(keys):
            nk = _norm_key(k)
            if not nk:
                return jsonify({"error": f"Invalid op_params.key at position {i}; expected [name, idx1, idx2].", "key": k}), 400
            norm_keys.append(nk)

        # Validate each values row length matches number of keys
        for i, row in enumerate(vals):
            if not isinstance(row, list) or len(row) != len(norm_keys):
                return jsonify({
                    "error": "Each row in 'op_params.value' must be a list with the same length as 'op_params.key'.",
                    "row_index": i,
                    "expected_length": len(norm_keys),
                    "actual": len(row) if isinstance(row, list) else None
                }), 400

        # Build ModelSimulationAgent indices (name, species, None, stream, gasOrSolid)
        # Last-index focus: we primarily use the last non-null index to resolve where the OP applies.
        # - [name, null, null]            → global (ignores nulls)
        # - [name, container, null]       → container-level (stream/gas/solid)
        # - [name, container?, species]   → species-level; if container is missing or mismatched,
        #                                    auto-resolve the unique container that contains the species.
        op_param_inds = []
        for name, idx1, idx2 in norm_keys:
            # Global parameter
            if idx1 is None and idx2 is None:
                op_param_inds.append((name, None, None, None, None))
                continue

            # Indexed by container only (last non-null is container)
            if idx2 is None:
                if idx1 in stms:
                    op_param_inds.append((name, None, None, idx1, None))
                elif idx1 in gass:
                    op_param_inds.append((name, None, None, None, idx1))
                elif idx1 in slds:
                    op_param_inds.append((name, None, None, None, idx1))
                else:
                    return jsonify({
                        "error": "Unknown index in op_params.key: container not found in context.basic.",
                        "key": [name, idx1, idx2]
                    }), 400
                continue

            # Species provided (idx2 not None). Focus on last index: resolve container automatically if needed.
            # 1) Try direct mapping when idx1 matches a known container containing the species
            direct_mapped = False
            if idx1 in stms:
                spc_list = ((basic.get("stm") or {}).get(idx1) or {}).get("spc") or []
                if idx2 in spc_list:
                    op_param_inds.append((name, idx2, None, idx1, None))
                    direct_mapped = True
            elif idx1 in gass:
                spc_list = ((basic.get("gas") or {}).get(idx1) or {}).get("spc") or []
                if idx2 in spc_list:
                    op_param_inds.append((name, idx2, None, None, idx1))
                    direct_mapped = True
            elif idx1 in slds:
                spc_list = ((basic.get("sld") or {}).get(idx1) or {}).get("spc") or []
                if idx2 in spc_list:
                    op_param_inds.append((name, idx2, None, None, idx1))
                    direct_mapped = True

            if direct_mapped:
                continue

            # 2) Auto-resolve: search all containers for a unique match of the species
            matches = []
            for stm in stms:
                spc_list = ((basic.get("stm") or {}).get(stm) or {}).get("spc") or []
                if idx2 in spc_list:
                    matches.append(("stm", stm))
            for gas in gass:
                spc_list = ((basic.get("gas") or {}).get(gas) or {}).get("spc") or []
                if idx2 in spc_list:
                    matches.append(("gas", gas))
            for sld in slds:
                spc_list = ((basic.get("sld") or {}).get(sld) or {}).get("spc") or []
                if idx2 in spc_list:
                    matches.append(("sld", sld))

            if not matches:
                return jsonify({
                    "error": "Species index not found in any stream/gas/solid in context.basic.",
                    "key": [name, idx1, idx2]
                }), 400
            if len(matches) > 1:
                return jsonify({
                    "error": "Ambiguous species index: found in multiple containers. Specify the container explicitly as the middle index.",
                    "key": [name, idx1, idx2],
                    "candidates": [{"type": t, "name": c} for (t, c) in matches]
                }), 400

            # Single match
            t, container = matches[0]
            if t == "stm":
                op_param_inds.append((name, idx2, None, container, None))
            else:
                # For gas or solid, both map to the 5th position in op_param tuple
                op_param_inds.append((name, idx2, None, None, container))

        sim_req = {
            "context": context,
            "op_params": {"ind": op_param_inds, "val": vals}
        }

        # Run simulation
        entity = g.graphdb_handler.query()
        sim_agent = ModelSimulationAgent(entity, sim_req)
        sim_res = sim_agent.simulate_scipy()

        # Empty result guard
        if sim_res is None or (isinstance(sim_res, list) and len(sim_res) == 0):
            return jsonify({"error": "Simulation returned no results."}), 404

        return jsonify(sim_res), 200

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

