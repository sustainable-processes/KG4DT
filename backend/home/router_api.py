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


def _load_case_context(case: str = "dushman", filename: str = "model_context.json"):
    """Load a case context JSON from the cases directory."""
    cases_dir = Path(current_app.root_path) / "cases"
    cases = [c for c in os.listdir(cases_dir) if not c.startswith(".")]
    if not case or case not in cases:
        return None

    print(f"Loading case context for case {case}...")
    print(f"filename: {filename}")
    context_file = cases_dir / case / filename
    if not os.path.exists(context_file):
        return None
    with open(context_file, "r", encoding="utf-8") as f:
        return json.load(f)



# APIs for model
# To remove.
@blueprint.route("/api/model", methods=["GET"])
def api_model():
    entity = g.graphdb_handler.query(mode="sidebar")
    return jsonify(entity)

# API: post with JSON body to specify filename (extensible for future needs)
# Body example:
# {
#   "case": "esterification",
#   "postfix": "moore"
# }
@blueprint.route("/api/model/context", methods=["GET", "POST"])
def api_model_context():
    data = request.get_json(silent=True) or {}
    case = data.get("case", "dushman")
    postfix = data.get("postfix", "model_context.json")

    if ".json" not in postfix:
        postfix = f"model_context_{postfix}.json"
    context = _load_case_context(case, postfix)
    if context is None:
        return jsonify({"error": "Case or context not found"}), 404
    return jsonify(context)



# APIs for structure

# Get only the information block of a case context
#    Body example (POST):
#    { "case": "dushman", "postfix": "model_context.json" }
#    GET also supports query params ?case=dushman&postfix=model_context.json
@blueprint.route("/api/model/information", methods=["GET", "POST"])
def api_model_information():
    data = request.get_json(silent=True) or {}

    # If body contains direct parameters (case-insensitive): ac, fp, mt, me, param_law, rxn
    direct_keys = {"ac", "fp", "mt", "me", "param_law", "rxn"}
    direct = {}
    if isinstance(data, dict):
        for k, v in data.items():
            lk = str(k).lower()
            if lk in direct_keys:
                direct[lk] = v

    if direct:
        # Build information from GraphDB using provided filters
        info = g.graphdb_handler.query_information(direct)
        return jsonify({"information": info}), 200

    # Otherwise, fallback to loading case context information
    case = data.get("case") if isinstance(data, dict) else None
    postfix = data.get("postfix") if isinstance(data, dict) else None

    # Fallback to query parameters for GET
    if request.method == "GET":
        case = case or request.args.get("case", "dushman")
        postfix = postfix or request.args.get("postfix", "model_context.json")

    if not case:
        return jsonify({"error": "Missing 'case'"}), 400
    if not postfix:
        postfix = "model_context.json"
    if ".json" not in postfix:
        postfix = f"model_context_{postfix}.json"

    context = _load_case_context(case, postfix)
    if context is None:
        return jsonify({"error": "Case or context not found"}), 404

    information = context.get("information", {})
    return jsonify({"information": information}), 200

# Get entity for the structure page (sidebar data)
@blueprint.route("/api/structure", methods=["GET"])
def api_structure():
    entity = g.graphdb_handler.query(mode="sidebar")
    return jsonify(entity)

# Get structure context via POST with JSON body
#    Body example:
#    {
#      "case": "dushman",
#      "postfix": "model_context.json",   // optional
#    }
@blueprint.route("/api/structure/context", methods=["GET", "POST"])
def api_structure_context():
    data = request.get_json(silent=True) or {}
    case = data.get("case", "dushman")
    postfix = data.get("postfix", "model_context.json")
    if ".json" not in postfix:
        postfix = f"model_context_{postfix}.json"
    context = _load_case_context(case, postfix)
    if context is None:
        return jsonify({"error": "Case or context not found"}), 404
    return jsonify(context)



# APIs for application
# To Remove
# Sidebar entity data used by application page
@blueprint.route("/api/application", methods=["GET"])
def api_application():
    entity = g.graphdb_handler.query(mode="sidebar")
    return jsonify(entity)


# Case context via POST body
#    Body example:
#    {
#      "case": "esterification",
#      "postfix": "ideal"                  # optional (ignored if filename provided)
#    }
@blueprint.route("/api/application/context", methods=["GET", "POST"])
def api_application_context():
    data = request.get_json(silent=True) or {}
    case = data.get("case", "dushman")
    postfix = data.get("postfix", "model_context.json")
    if ".json" not in postfix:
        postfix = f"model_context_{postfix}.json"
    context = _load_case_context(case, postfix)
    if context is None:
        return jsonify({"error": "Case or context not found"}), 404
    return jsonify(context)



# Knowledge Graph APIs
# 1) Get entity used by knowledge graph with mainpage
#    Example: /api/knowledge_graph/mainpage
@blueprint.route("/api/knowledge_graph/mainpage", methods=["GET"])
def api_knowledge_graph_entity():
    entity = g.graphdb_handler.query(mode="mainpage")
    return jsonify(entity)


# 2) Get computed knowledge graph data from sidebar
# To Remove
#    Example: /api/knowledge_graph/sidebar
@blueprint.route("/api/knowledge_graph/sidebar", methods=["GET"])
def api_knowledge_graph_data():
    entity = g.graphdb_handler.query(mode="sidebar")
    knowledge_graph_data = ModelKnowledgeGraphAgent(entity).to_knowledge_graph_data()
    return jsonify(knowledge_graph_data)


# 3) Get case context for knowledge graph via GET
#    Optional query params:
#      - filename: exact file inside the case directory
#      - postfix: builds filename as top_down_rule_model_context_<postfix>.json (ignored if filename provided)
#    Defaults to top_down_rule_model_context.json
@blueprint.route("/api/knowledge_graph/context/<path:case>", methods=["GET"])
def api_knowledge_graph_context_case(case):
    filename = "top_down_rule_model_context.json"
    context = _load_case_context(case, filename)
    if context is None:
        return jsonify({"error": "Case or context not found"}), 404
    return jsonify(context)


# 4) Get case context for knowledge graph via POST
#    Body example:
#    {
#      "case": "esterification",
#      "postfix": "custom"
#    }
@blueprint.route("/api/knowledge_graph/context", methods=["POST"])
def api_knowledge_graph_context():
    data = request.get_json(silent=True) or {}
    case = data.get("case")
    postfix = data.get("postfix", "top_down_rule_model_context.json")
    if ".json" not in postfix:
        postfix = f"top_down_{postfix}_model_context.json"

    context = _load_case_context(case, postfix)
    if context is None:
        return jsonify({"error": "Case or context not found"}), 404
    return jsonify(context)



@blueprint.route("/api/solvent", methods=["POST"])
def api_solvent():
    """
    Request JSON:
    {
      "solvents": ["water", "ethanol", "acetone"],
      "properties": ["Density", "Viscosity"],      # optional; defaults shown
      "property_sources": ["pubchem", "wikipedia", "chemspider"],  # optional
      "include_miscibility": true                  # optional; default true
    }

    Response JSON:
    {
      "solvents": [...],
      "properties": {
        "pubchem": { "<solvent>": { "<prop>": <value or null>, ... }, ... },
        "wikipedia": { ... },
        "chemspider": { ... },
        "merged": { "<solvent>": { "<prop>": <value or null>, ... }, ... }
      },
      "miscibility": {
        "source": "sigma-aldrich",
        "matrix": { "<solventA>": { "<solventB>": "<result>", ... }, ... }
      }
    }
    """
    # Input parsing and defaults
    payload = request.get_json(silent=True) or {}
    solvents = payload.get("solvents") or []
    if not isinstance(solvents, list) or not solvents:
        return jsonify({"error": "Field 'solvents' must be a non-empty list of solvent names."}), 400

    requested_properties = payload.get("properties") or ["Density", "Viscosity"]
    if not isinstance(requested_properties, list) or not requested_properties:
        return jsonify({"error": "Field 'properties' must be a non-empty list when provided."}), 400

    property_sources = payload.get("property_sources") or ["pubchem", "wikipedia", "chemspider"]
    if not isinstance(property_sources, list) or not property_sources:
        return jsonify({"error": "Field 'property_sources' must be a non-empty list when provided."}), 400

    include_miscibility = payload.get("include_miscibility", True)

    # Setup shared entity
    entity = g.graphdb_handler.query()

    # Collect properties from enabled sources
    properties = {}
    physical_property_agent = PhysicalPropertyAgent(entity)

    if "pubchem" in property_sources:
        try:
            properties["pubchem"] = physical_property_agent.query_pubchem(solvents, requested_properties)
        except Exception as e:
            properties["pubchem"] = {"error": str(e)}

    if "wikipedia" in property_sources:
        try:
            properties["wikipedia"] = physical_property_agent.query_wikipedia(solvents, requested_properties)
        except Exception as e:
            properties["wikipedia"] = {"error": str(e)}

    if "chemspider" in property_sources:
        # Note: existing chemspider implementation appears to support Density primarily
        try:
            properties["chemspider"] = physical_property_agent.query_chemspider(solvents, requested_properties)
        except Exception as e:
            properties["chemspider"] = {"error": str(e)}

    # Simple merge strategy: first non-null by source priority order
    merged = {}
    source_priority = [s for s in ["pubchem", "wikipedia", "chemspider"] if s in property_sources]
    for s in solvents:
        merged[s] = {}
        for prop in requested_properties:
            value = None
            for src in source_priority:
                src_dict = properties.get(src, {})
                if isinstance(src_dict, dict):
                    s_vals = src_dict.get(s) if s in src_dict else None
                    if isinstance(s_vals, dict) and prop in s_vals and s_vals[prop] is not None:
                        value = s_vals[prop]
                        break
            merged[s][prop] = value
    properties["merged"] = merged

    # Miscibility
    miscibility = None
    if include_miscibility:
        try:
            data_path = Path(current_app.root_path) / "data" / "solvent_miscibility_table.csv"
            solvent_miscibility_agent = SolventMiscibilityAgent(entity, str(data_path))
            miscibility_matrix = solvent_miscibility_agent.query_sigmaaldrich(solvents)
            miscibility = {
                "source": "sigma-aldrich",
                "matrix": miscibility_matrix
            }
        except Exception as e:
            miscibility = {"error": str(e)}

    response = {
        "solvents": solvents,
        "properties": properties,
        "miscibility": miscibility
    }
    return jsonify(response), 200


#### Process Definition
@blueprint.route("/api/model/var", methods=["GET", "POST"])
def api_model_var():
    response = g.graphdb_handler.query_model_variable()
    return jsonify(response), 200

@blueprint.route("/api/model/unit", methods=["GET", "POST"])
def api_model_unit():
    response = g.graphdb_handler.query_unit()
    return jsonify(response), 200

@blueprint.route("/api/model/save", methods=["POST"])
def api_model_save():
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"error": "Invalid or missing JSON body"}), 400

    users = payload.get("users") or {}
    if not isinstance(users, dict):
        return jsonify({"error": "Field 'users' must be an object"}), 400

    # Basic validation for list-type fields when present
    for key in ("s", "v", "p"):
        if key in payload and not isinstance(payload[key], list):
            return jsonify({"error": f"Field '{key}' must be a list"}), 400

    # Prepare save directory: <project_root>/save
    save_dir = Path(current_app.root_path) / "save"
    save_dir.mkdir(parents=True, exist_ok=True)

    # Build a descriptive, collision-resistant filename
    user_id = users.get("id", "unknown")
    project_name = users.get("project_name", "project")
    model_name = users.get("model", "model")

    # Sanitize components and append UTC timestamp
    def _safe(s):
        return str(s).replace(os.sep, "_").replace(" ", "_")

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    filename = f"{_safe(project_name)}_{_safe(model_name)}_{_safe(user_id)}_{timestamp}.json"
    file_path = save_dir / filename

    # Write the full payload to JSON
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return jsonify({"error": f"Failed to save file: {e}"}), 500

    return jsonify({"success": True, "file": filename, "path": str(file_path.relative_to(current_app.root_path))}), 200


@blueprint.route("/api/model/load", methods=["GET"])
def api_model_load():
    project_name = request.args.get("project_name")
    model = request.args.get("model")            # optional
    user_id = request.args.get("user_id")        # optional
    if not project_name:
        return jsonify({"error": "Missing required query parameter 'project_name'"}), 400

    save_dir = Path(current_app.root_path) / "save"
    if not save_dir.exists() or not save_dir.is_dir():
        return jsonify({"error": "No saved data directory found"}), 404

    # Use the same sanitization that save used
    def _safe(s):
        return str(s).replace(os.sep, "_").replace(" ", "_")

    # Build search pattern: {project}_{model}_{user_id}_{timestamp}.json
    # If model/user_id not provided, use wildcard to match any.
    proj = _safe(project_name)
    mdl = _safe(model) if model else "*"
    uid = _safe(user_id) if user_id else "*"
    pattern = f"{proj}_{mdl}_{uid}_*.json"

    candidates = [p for p in save_dir.glob(pattern) if p.is_file()]
    if not candidates:
        detail = {"project_name": project_name}
        if model:
            detail["model"] = model
        if user_id:
            detail["user_id"] = user_id
        return jsonify({"error": "No saved files found for given filters", "filters": detail}), 404

    # Pick the most recently modified file
    latest = max(candidates, key=lambda p: p.stat().st_mtime)

    try:
        with open(latest, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return jsonify({"error": f"Failed to load file '{latest.name}': {e}"}), 500

    return jsonify({"success": True, "file": latest.name, "data": data}), 200



@blueprint.route("/api/model/phenomenon", methods=["GET"])
def api_model_phenomenon():
    # Query the database for the phenomenon
    entity = g.graphdb_handler.query_phenomenon()
    return jsonify(entity)

@blueprint.route("/api/model/phenomenon/ac", methods=["GET"])
def api_model_phenomenon_ac():
    entity = g.graphdb_handler.query_accumulators()
    return jsonify(entity)

@blueprint.route("/api/model/phenomenon/fp", methods=["GET"])
def api_model_phenomenon_fp():
    try:
        raw_ac = request.args.get("method")
        if raw_ac is None or str(raw_ac).strip() == "":
            return jsonify({
                "error": "Missing required query parameter 'method'. Allowed values: 'Batch', 'Continuous'.",
                "hint": "Example: /api/model/phenomenon/fp?ac=Batch"
            }), 400

        ac_norm = str(raw_ac).strip().lower()
        allowed = {"batch", "continuous"}
        if ac_norm not in allowed:
            return jsonify({
                "error": "Invalid value for 'method'. Allowed values are 'Batch' or 'Continuous'.",
                "received": raw_ac
            }), 400

        # Query the database for the phenomenon
        entity = g.graphdb_handler.query_phenomenon_ac(ac_norm)

        # Handle empty result sets gracefully
        if entity is None:
            return jsonify({
                "error": "No phenomenon found for the specified operating condition.",
                "method": raw_ac
            }), 404

        # If it's a collection, also consider emptiness
        if isinstance(entity, (list, dict)) and len(entity) == 0:
            return jsonify({
                "error": "No phenomenon found for the specified operating condition.",
                "method": raw_ac
            }), 404

        return jsonify(entity), 200

    except Exception as e:
        # Unexpected error
        return jsonify({
            "error": "Internal server error while processing the request.",
            "detail": str(e)
        }), 500


@blueprint.route("/api/model/phenomenon/mt", methods=["GET"])
def api_model_phenomenon_mt():
    try:
        # Accept multiple aliases for the flow pattern parameter for flexibility
        raw_fp = request.args.get("fp")
        if raw_fp is None or str(raw_fp).strip() == "":
            return jsonify({
                "error": "Missing required query parameter 'pattern' (aliases: 'fp', 'flow_pattern').",
                "hint": "Example: /api/model/phenomenon/mt?fp=Annular_Microflow"
            }), 400

        # Delegate to graphdb handler to get mass transfer phenomena linked to the FlowPattern
        mts = g.graphdb_handler.query_mass_transfer_by_flow_pattern(raw_fp)

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

@blueprint.route("/api/model/phenomenon/me", methods=["GET"])
def api_model_phenomenon_me():
    try:
        # Primary mode: accept JSON body with an array of mass transfer names
        payload = request.get_json(silent=True) or {}
        mt_list = payload.get("mt") if isinstance(payload, dict) else None

        if isinstance(mt_list, list) and len(mt_list) > 0:
            result_set = set()
            for item in mt_list:
                if item is None or str(item).strip() == "":
                    continue
                equilibria = g.graphdb_handler.query_mass_equilibrium_by_mass_transfer(item)
                for eq in (equilibria or []):
                    if eq:
                        result_set.add(eq)
            if not result_set:
                return jsonify({
                    "error": "No mass equilibrium found for the specified mass transfer phenomena.",
                    "mt": mt_list
                }), 404
            return jsonify({"me": sorted(result_set)}), 200

    except Exception as e:
        return jsonify({
            "error": "Internal server error while processing the request.",
            "detail": str(e)
        }), 500


@blueprint.route("/api/model/phenomenon/param_law", methods=["POST", "GET"])
def api_model_param_law():
    """
    Retrieve parameter -> law mapping constrained by selected phenomena.
    Accepts either:
      - POST JSON body with any of keys: ac, fp, mt, me (string or list)
      - GET query params: ac, fp, mt, me (can be repeated or comma-separated)

    Response: {"param_law": {"<Parameter>": "<Law>", ...}}
    """
    try:
        payload = request.get_json(silent=True) or {}
        filters = {}
        keys = ("ac", "fp", "mt", "me")

        for k in keys:
            val = payload.get(k) if isinstance(payload, dict) else None
            if val is None and request.method == "GET":
                # Support multiple via ?k=a&k=b or comma-separated ?k=a,b
                lst = request.args.getlist(k)
                if not lst:
                    s = request.args.get(k)
                    if s:
                        lst = [part.strip() for part in s.split(",") if part.strip()]
                val = lst if lst else None
            if val is not None:
                filters[k] = val

        if not any(filters.get(k) for k in keys):
            return jsonify({
                "error": "Provide at least one of 'ac', 'fp', 'mt', or 'me' via JSON body or query params.",
                "hint": {
                    "POST": {"ac": "Batch", "fp": "Well_Mixed", "mt": ["Gas-Liquid_Mass_Transfer"], "me": ["Gas_Dissolution_Equilibrium"]},
                    "GET": "/api/model/phenomenon/param_law?fp=Annular_Microflow&mt=Engulfment"
                }
            }), 400

        mapping = g.graphdb_handler.query_param_law(filters)
        if not mapping:
            return jsonify({
                "error": "No parameter law found for the specified filters.",
                "filters": filters
            }), 404

        return jsonify({"param_law": mapping}), 200

    except Exception as e:
        return jsonify({
            "error": "Internal server error while processing the request.",
            "detail": str(e)
        }), 500



@blueprint.route("/api/model/phenomenon/rxn", methods=["POST", "GET"])
def api_model_reactions():
    """
    Retrieve reactions (ChemicalReactionPhenomenon) and their associated kinetic law names.
    Accepts either:
      - POST JSON body with any of keys: ac, fp, mt, me, param_law (string, list, or dict)
      - GET query params: ac, fp, mt, me, param_law (can be repeated or comma-separated)

    Response: {"rxn": {"<Reaction>": ["<Law>", ...], ...}}
    """
    try:
        payload = request.get_json(silent=True) or {}
        filters = {}
        keys = ("ac", "fp", "mt", "me", "param_law")

        for k in keys:
            val = payload.get(k) if isinstance(payload, dict) else None
            if val is None and request.method == "GET":
                lst = request.args.getlist(k)
                if not lst:
                    s = request.args.get(k)
                    if s:
                        lst = [part.strip() for part in s.split(",") if part.strip()]
                val = lst if lst else None
            if val is not None:
                filters[k] = val

        # Require at least one of the accepted filters including param_law
        if not any(filters.get(k) for k in keys):
            return jsonify({
                "error": "Provide at least one of 'ac', 'fp', 'mt', 'me', or 'param_law' via JSON body or query params.",
                "hint": {
                    "POST": {"param_law": ["Arrhenius", "Plain_Rate_Constant"]},
                    "GET": "/api/model/phenomenon/rxn?param_law=Arrhenius&fp=Annular_Microflow"
                }
            }), 400

        mapping = g.graphdb_handler.query_reactions(filters)
        if not mapping:
            return jsonify({
                "error": "No reactions found for the specified filters.",
                "filters": filters
            }), 404

        return jsonify({"rxn": mapping}), 200

    except Exception as e:
        return jsonify({
            "error": "Internal server error while processing the request.",
            "detail": str(e)
        }), 500
