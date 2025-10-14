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


@blueprint.route("/api/model/pheno", methods=["GET"])
def api_model_pheno():
    # Query the database for the phenomenon
    pheno_dict = g.graphdb_handler.query_pheno()
    return jsonify(pheno_dict)


@blueprint.route("/api/model/pheno/ac", methods=["GET"])
def api_model_pheno_ac():
    acs = g.graphdb_handler.query_ac()
    return jsonify(acs)


@blueprint.route("/api/model/pheno/fp", methods=["GET"])
def api_model_pheno_fp():
    try:
        raw_ac = request.args.get("ac")
        if raw_ac is None or str(raw_ac).strip() == "":
            return jsonify({
                "error": "Missing required query parameter 'ac'. Allowed values: 'Batch', 'Continuous'.",
                "hint": "Example: /api/model/pheno/fp?ac=Batch"
            }), 400

        ac_norm = str(raw_ac).strip().lower()
        allowed = {"batch", "continuous", "cstr"}
        if ac_norm not in allowed:
            return jsonify({
                "error": "Invalid value for 'ac'. Allowed values are 'Batch' or 'Continuous' or 'CSTR'.",
                "received": raw_ac
            }), 400

        # Query the database for the phenomenon
        fps = g.graphdb_handler.query_fp_by_ac(ac_norm)

        # Handle empty result sets gracefully
        if fps is None:
            return jsonify({
                "error": "No phenomenon found for the specified operating condition.",
                "method": raw_ac
            }), 404

        # If it's a collection, also consider emptiness
        if isinstance(fps, (list, dict)) and len(fps) == 0:
            return jsonify({
                "error": "No phenomenon found for the specified operating condition.",
                "method": raw_ac
            }), 404

        return jsonify(fps), 200

    except Exception as e:
        # Unexpected error
        return jsonify({
            "error": "Internal server error while processing the request.",
            "detail": str(e)
        }), 500


@blueprint.route("/api/model/pheno/mt", methods=["GET"])
def api_model_pheno_mt():
    try:
        # Accept multiple aliases for the flow pattern parameter for flexibility
        raw_fp = request.args.get("fp")
        if raw_fp is None or str(raw_fp).strip() == "":
            return jsonify({
                "error": "Missing required query parameter 'pattern' (aliases: 'fp', 'flow_pattern').",
                "hint": "Example: /api/model/phenomenon/mt?fp=Annular_Microflow"
            }), 400

        # Delegate to graphdb handler to get mass transfer phenomena linked to the FlowPattern
        mts = g.graphdb_handler.query_mt_by_fp(raw_fp)

        if mts is None or (isinstance(mts, (list, dict)) and len(mts) == 0):
            return jsonify({
                "error": "No mass transfer phenomenon found for the specified flow pattern.",
                "pattern": raw_fp
            }), 404

        return jsonify(mts), 200

    except Exception as e:
        return jsonify({
            "error": "Internal server error while processing the request.",
            "detail": str(e)
        }), 500


@blueprint.route("/api/model/pheno/me", methods=["GET"])
def api_model_pheno_me():
    try:
        # Accept 'mt' from JSON body (POST/GET) or from query params when GET
        if request.method == "POST" and not request.is_json:
            return jsonify({"error": "Unsupported Media Type. Use Content-Type: application/json."}), 415

        payload = request.get_json(silent=True) or {}
        mt_list = payload.get("mt") if isinstance(payload, dict) else None

        if (not mt_list) and request.method == "GET":
            lst = request.args.getlist("mt")
            if not lst:
                s = request.args.get("mt")
                if s:
                    lst = [p.strip() for p in s.split(",") if p.strip()]
            mt_list = lst if lst else None

        # Validate input
        if not mt_list or not isinstance(mt_list, list):
            return jsonify({
                "error": "Provide one or more 'mt' (mass transport) names in JSON body or query params.",
                "hint": {"POST": {"mt": ["Engulfment"]}, "GET": "/api/model/pheno/me?mt=Engulfment"}
            }), 400

        mes = set()
        for item in mt_list:
            if item is None or str(item).strip() == "":
                continue
            mt_mes = g.graphdb_handler.query_me_by_mt(item)
            for me in (mt_mes or []):
                if me:
                    mes.add(me)
        if not mes:
            return jsonify({
                "error": "No mass equilibrium found for the specified mass transport phenomena.",
                "mt": mt_list
            }), 404
        return jsonify({"me": sorted(mes)}), 200

    except Exception as e:
        return jsonify({
            "error": "Internal server error while processing the request.",
            "detail": str(e)
        }), 500


@blueprint.route("/api/model/pheno/param_law", methods=["GET"])
def api_model_param_law():
    """
    Retrieve parameter -> law mapping constrained by selected phenomena.
    Accepts either:
      - GET JSON body with any of keys: ac, fp, mt, me (string or list)

    Response: {"param_law": {"<Parameter>": "<Law>", ...}}
    """
    try:
        if request.method == "POST" and not request.is_json:
            return jsonify({"error": "Unsupported Media Type. Use Content-Type: application/json."}), 415
        desc = request.get_json(silent=True) or {}
        keys = ("ac", "fp", "mt", "me")

        for k in keys:
            val = desc.get(k) if isinstance(desc, dict) else None
            if val is None and request.method == "GET":
                # Support multiple via ?k=a&k=b or comma-separated ?k=a,b
                lst = request.args.getlist(k)
                if not lst:
                    s = request.args.get(k)
                    if s:
                        lst = [part.strip() for part in s.split(",") if part.strip()]
                val = lst if lst else None
            if val is not None:
                desc[k] = val

        if not any(desc.get(k) for k in keys):
            return jsonify({
                "error": "Provide at least one of 'ac', 'fp', 'mt', or 'me' via JSON body or query params.",
                "hint": {
                    "POST": {"ac": "Batch", "fp": "Well_Mixed", "mt": ["Gas-Liquid_Mass_Transfer"], "me": ["Gas_Dissolution_Equilibrium"]},
                    "GET": "/api/model/phenomenon/param_law?fp=Annular_Microflow&mt=Engulfment"
                }
            }), 400

        param_law = g.graphdb_handler.query_param_law(desc)

        # ac = desc["ac"] if "ac" in desc else None
        # fp = desc["fp"] if "fp" in desc else None
        # mts = desc["mt"] if "mt" in desc else []
        # mes = desc["me"] if "me" in desc else []

        # param_law = {}
        # vars = g.graphdb_handler.query_var()
        # laws = g.graphdb_handler.query_law(mode="mainpage")

        # # flow pattern laws subsidiary to mass transport
        # for law_dict in laws.values():
        #     if law_dict["pheno"] not in mts:
        #         continue
        #     for var in law_dict["vars"]:
        #         if var == "Concentration":
        #             continue
        #         if var in param_law or not vars[var]["laws"]:
        #             continue
        #         var_laws = []
        #         for var_law in vars[var]["laws"]:
        #             if laws[var_law]["pheno"] == fp:
        #                 var_laws.append(var_law)
        #         if var_laws:
        #             param_law[var] = var_laws

        # # flow pattern laws subsidiary to flow pattern
        # for law_dict in laws.values():
        #     if law_dict["pheno"] != fp:
        #         continue
        #     for var in law_dict["vars"]:
        #         if var == "Concentration":
        #             continue
        #         if var in param_law or not vars[var]["laws"]:
        #             continue
        #         var_laws = []
        #         for var_law in vars[var]["laws"]:
        #             if laws[var_law]["pheno"] == fp:
        #                 var_laws.append(var_law)
        #         if var_laws:
        #             param_law[var] = var_laws

        # # mass equilibrium laws
        # for law_dict in laws.values():
        #     if law_dict["pheno"] not in mts:
        #         continue
        #     for var in law_dict["vars"]:
        #         if var in param_law or not vars[var]["laws"]:
        #             continue
        #         var_laws = []
        #         for var_law in vars[var]["laws"]:
        #             if laws[var_law]["pheno"] in mes:
        #                 var_laws.append(var_law)
        #         if var_laws:
        #             param_law[var] = var_laws

        return jsonify(param_law), 200

    except Exception as e:
        return jsonify({
            "error": "Internal server error while processing the request.",
            "detail": str(e)
        }), 500


@blueprint.route("/api/model/pheno/rxn", methods=["GET"])
def api_model_rxn():
    """
    Retrieve Reaction Phenomena.
    - By default (no filters), returns a list of all ReactionPhenomenon names.
    - Filters MUST be provided in the JSON body (GET). Query parameters are not supported.
      Supported JSON keys (string or list of strings):
        ac | accumulation: Accumulation name(s)
        fp | flow_pattern: Flow pattern name(s)
        mt | mass_transport: Mass transport phenomenon name(s)
        me | mass_equilibrium: Mass equilibrium phenomenon name(s)
        param | parameter: Parameter/ModelVariable name(s) present in the associated law
        law | law_name | laws: Law name(s)
        param_law: JSON mapping of { parameter: law } or list of such mappings

    Examples:
      - GET /api/model/pheno/rxn with empty body                -> all reactions
      - POST /api/model/pheno/rxn with body {"ac": "Batch", "fp": "Well_Mixed"}
      - POST body {"param": ["k_La", "Interfacial_Area"]}
      - POST body {"law": ["Arrhenius_Rate_Law"]}
      - POST body {"mt": ["Engulfment"], "me": ["Gas_Dissolution_Equilibrium"]}
    """
    try:
        if request.method == "POST" and not request.is_json:
            return jsonify({"error": "Unsupported Media Type. Use Content-Type: application/json."}), 415
        body = request.get_json(silent=True) or {}

        # Reject use of query parameters for filters
        forbidden_keys = [
            "ac", "accumulation",
            "fp", "flow_pattern",
            "mt", "mass_transport",
            "me", "mass_equilibrium",
            "param", "parameter",
            "law", "law_name", "laws",
            "param_law",
        ]
        forbidden_in_args = {k: request.args.getlist(k) for k in forbidden_keys if request.args.getlist(k)}
        if forbidden_in_args:
            return jsonify({
                "error": "Pass filters in the request JSON body. Query parameters are not supported for this endpoint.",
                "forbidden_query_params": forbidden_in_args,
                "hint": {
                    "body": {"ac": "Batch", "fp": "Well_Mixed", "mt": ["Engulfment"], "me": ["Gas_Dissolution_Equilibrium"]}
                }
            }), 400

        def _collect_list(primary, aliases=None):
            aliases = aliases or []
            # Only read from body
            val = body.get(primary) if isinstance(body, dict) else None
            if val is None:
                for a in aliases:
                    if isinstance(body, dict) and a in body:
                        val = body.get(a)
                        break
            # Normalize to list
            if val is None:
                return []
            if isinstance(val, list):
                return [str(x).strip() for x in val if x is not None and str(x).strip() != ""]
            return [str(val).strip()] if str(val).strip() != "" else []

        filters = {}
        ac_list = _collect_list("ac", ["accumulation"])  # Batch / Continuous
        fp_list = _collect_list("fp", ["flow_pattern"])  # Flow pattern
        mt_list = _collect_list("mt", ["mass_transport"])  # Mass transport phenomenon
        me_list = _collect_list("me", ["mass_equilibrium"])  # Mass equilibrium phenomenon
        param_list = _collect_list("param", ["parameter"])  # Variables used in laws
        law_list = _collect_list("law", ["law_name", "laws"])  # Law names

        if ac_list:
            filters["ac"] = ac_list
        if fp_list:
            filters["fp"] = fp_list
        if mt_list:
            filters["mt"] = mt_list
        if me_list:
            filters["me"] = me_list
        if param_list:
            filters["param"] = param_list
        if law_list:
            filters["law"] = law_list

        # param_law only from JSON body
        if isinstance(body, dict) and "param_law" in body and body.get("param_law") is not None:
            filters["param_law"] = body.get("param_law")

        # If no filters, return the unfiltered list (backward compatible)
        if not filters:
            rxns = g.graphdb_handler.query_rxn()
            return jsonify(rxns), 200

        rxns = g.graphdb_handler.query_rxn(filters)
        if not rxns:
            return jsonify({
                "error": "No reaction phenomenon matched the provided filters.",
                "filters": filters
            }), 404
        return jsonify(rxns), 200

    except Exception as e:
        return jsonify({
            "error": "Internal server error while processing the request.",
            "detail": str(e)
        }), 500

