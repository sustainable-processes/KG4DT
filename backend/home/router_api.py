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

# API: post with JSON body to specify filename (extensible for future needs)
# Body example:
# {
#   "case": "esterification",
#   "postfix": "moore"
# }
@blueprint.route("/api/model/context", methods=["GET"])
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


# Get only the information block of a case context
#    Body example (GET):
@blueprint.route("/api/model/info", methods=["GET"])
def api_model_information():
    context = request.get_json(silent=True) or {}
    info = g.graphdb_handler.query_info(context)
    return jsonify(info), 200

# Get structure context via POST with JSON body
#    Body example:
#    {
#      "case": "dushman",
#      "postfix": "model_context.json",   // optional
#    }
@blueprint.route("/api/structure/context", methods=["GET"])
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
@blueprint.route("/api/knowledge_graph", methods=["GET"])
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
@blueprint.route("/api/knowledge_graph/context", methods=["GET"])
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



@blueprint.route("/api/solvent", methods=["GET"])
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
@blueprint.route("/api/model/var", methods=["GET"])
def api_model_var():
    response = g.graphdb_handler.query_var()
    return jsonify(response), 200

@blueprint.route("/api/model/unit", methods=["GET"])
def api_model_unit():
    response = g.graphdb_handler.query_unit()
    return jsonify(response), 200

@blueprint.route("/api/model/save", methods=["POST"])
def api_model_save():
    # Enforce JSON input
    if not request.is_json:
        return jsonify({"error": "Unsupported Media Type. Use Content-Type: application/json."}), 415

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Invalid or missing JSON body; expected a JSON object."}), 400

    users = payload.get("users") or {}
    if not isinstance(users, dict):
        return jsonify({"error": "Field 'users' must be an object"}), 400

    # Basic validation for list-type fields when present
    for key in ("s", "v", "p"):
        if key in payload and not isinstance(payload[key], list):
            return jsonify({"error": f"Field '{key}' must be a list"}), 400

    # Persist to database using Project model
    try:
        from ..models import get_session
        from ..models.project import Project

        session = get_session()
        name = users.get("project_name") or users.get("name") or "project"
        model_name = users.get("model")
        try:
            user_id = int(users.get("id")) if users.get("id") is not None else None
        except Exception:
            user_id = None

        # Upsert: replace content when a project exists with same (name, model, user_id)
        existing = (
            session.query(Project)
            .filter(
                Project.name == name,
                Project.model == model_name,
                Project.user_id == user_id,
            )
            .one_or_none()
        )

        # Store payload without the 'users' field
        payload_no_users = {k: v for k, v in payload.items() if k != "users"}

        if existing is not None:
            existing.content = payload_no_users
            # last_update will auto-update via onupdate; flush to generate UPDATE
            session.commit()
            return jsonify({
                "success": True,
                "id": existing.id,
                "name": existing.name,
                "model": existing.model,
                "user_id": existing.user_id,
                "replaced": True,
            }), 200
        else:
            project_row = Project(name=name, user_id=user_id, model=model_name, content=payload_no_users)
            session.add(project_row)
            session.commit()
            return jsonify({
                "success": True,
                "id": project_row.id,
                "name": project_row.name,
                "model": project_row.model,
                "user_id": user_id,
                "replaced": False,
            }), 200
    except Exception as e:
        # Attempt rollback if session exists
        try:
            session.rollback()
        except Exception:
            pass
        return jsonify({"error": f"Failed to save to database: {e}"}), 500

@blueprint.route("/api/model/load", methods=["GET"])
def api_model_load():
    project_name = request.args.get("project_name")
    model = request.args.get("model")            # optional
    user_id = request.args.get("user_id")        # optional
    if not project_name:
        return jsonify({"error": "Missing required query parameter 'project_name'"}), 400

    try:
        from ..models import get_session
        from ..models.project import Project
        session = get_session()

        q = session.query(Project).filter(Project.name == project_name)
        if model:
            q = q.filter(Project.model == model)
        if user_id is not None and str(user_id).strip() != "":
            try:
                q = q.filter(Project.user_id == int(user_id))
            except Exception:
                # If user_id not an int, return 400
                return jsonify({"error": "Query parameter 'user_id' must be an integer"}), 400

        # Order by last_update desc then datetime desc to get latest
        q = q.order_by(Project.last_update.desc(), Project.datetime.desc())
        row = q.first()
        if not row:
            detail = {"project_name": project_name}
            if model:
                detail["model"] = model
            if user_id:
                detail["user_id"] = user_id
            return jsonify({"error": "No saved records found for given filters", "filters": detail}), 404

        # Return the payload as saved (which excludes 'users');
        # for backward compatibility, also strip 'users' if present in older records.
        content = row.content
        try:
            if isinstance(content, dict) and 'users' in content:
                content = {k: v for k, v in content.items() if k != 'users'}
        except Exception:
            pass
        return jsonify(content), 200
    except Exception as e:
        return jsonify({"error": f"Failed to load from database: {e}"}), 500


@blueprint.route("/api/model/list_project", methods=["GET"])
def api_model_list_project():
    """List all projects for a given user.

    Query parameters:
    - user_id (required, int): The user ID to list projects for.
    - model (optional, str): Filter by model name.
    - limit (optional, int >= 0, default 100): Max number of rows to return.
    - offset (optional, int >= 0, default 0): Number of rows to skip.

    Response (200):
    {
      "projects": [
        {"id": 1, "name": "ProjA", "model": "Well_Mixed", "datetime": "...", "last_update": "..."},
        ...
      ],
      "count": <int>  // number of items returned in this page
    }

    Errors:
    - 400: missing/invalid user_id
    - 500: server/database error
    """
    user_id = request.args.get("user_id")
    if user_id is None or str(user_id).strip() == "":
        return jsonify({"error": "Missing required query parameter 'user_id'"}), 400

    try:
        uid = int(user_id)
    except Exception:
        return jsonify({"error": "Query parameter 'user_id' must be an integer"}), 400

    model = request.args.get("model")

    def _get_int_qp(name, default):
        val = request.args.get(name)
        if val is None or str(val).strip() == "":
            return default
        try:
            num = int(val)
            return num if num >= 0 else default
        except Exception:
            return default

    limit = _get_int_qp("limit", 100)
    offset = _get_int_qp("offset", 0)

    try:
        from ..models import get_session
        from ..models.project import Project
        session = get_session()

        q = session.query(Project).filter(Project.user_id == uid)
        if model:
            q = q.filter(Project.model == model)

        # Order latest-first for usability
        q = q.order_by(Project.last_update.desc(), Project.datetime.desc(), Project.id.desc())

        if offset:
            q = q.offset(offset)
        if limit:
            q = q.limit(limit)

        rows = q.all()

        def _iso(dt):
            try:
                return dt.isoformat() if dt is not None else None
            except Exception:
                return None

        projects = [
            {
                "id": row.id,
                "name": row.name,
                "model": row.model,
                "datetime": _iso(row.datetime),
                "last_update": _iso(row.last_update),
            }
            for row in rows
        ]

        return jsonify({"projects": projects, "count": len(projects)}), 200

    except Exception as e:
        return jsonify({"error": "Failed to list projects from database.", "detail": str(e)}), 500
