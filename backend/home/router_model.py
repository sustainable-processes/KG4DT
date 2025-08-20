import os
import json
from io import BytesIO
from pathlib import Path
from flask import (
    g, jsonify, render_template, request, send_file,
    current_app
)
from . import blueprint
from ..utils.model_agent import ModelAgent
from ..utils.model_calibration_agent import ModelCalibrationAgent
from ..utils.model_exploration_agent import ModelExplorationAgent
from ..utils.model_simulation_agent import ModelSimulationAgent


@blueprint.route("/model")
def model():
    entity = g.graphdb_handler.query(mode="sidebar")
    entity_json = json.dumps(entity)
    model_context_json = """
        if (sessionStorage.getItem('modelContext')) {
            var modelContext = JSON.parse(sessionStorage.getItem('modelContext'));
        };
    """
    return render_template("home/model.html", entity=entity, entity_json=entity_json, model_context_json=model_context_json)

@blueprint.route("/model/<path:case>")
def model_case(case):
    cases_dir = Path(current_app.root_path) / "cases"
    cases = [c for c in os.listdir(cases_dir) if not c.startswith(".")]
    if case and case in cases:
        context_file = cases_dir / case / "model_context.json"
        if os.path.exists(context_file):
            model_context_json = f"var modelContext = {json.dumps(json.load(open(context_file, 'r')))}\n" + \
                                 "sessionStorage.removeItem('modelContext');"
            entity = g.graphdb_handler.query(mode="sidebar")
            entity_json = f"var entity = {json.dumps(entity)}"
            return render_template("home/model.html", entity=entity, entity_json=entity_json, model_context_json=model_context_json)
    return render_template("home/page-404.html")


@blueprint.route("/model/fp/<case>")
def model_case_postfix(case, postfix):
    cases_dir = Path(current_app.root_path) / "cases"
    cases = [c for c in os.listdir(cases_dir) if not c.startswith(".")]
    if case and case in cases:
        context_filename = f"model_context_{postfix}.json"
        context_file = cases_dir / case / context_filename
        if context_filename in os.listdir(cases_dir / case):
            model_context_json = f"var modelContext = {json.dumps(json.load(open(context_file, 'r')))}\n" + \
                                 "sessionStorage.removeItem('modelContext');"
            entity = g.graphdb_handler.query(mode="sidebar")
            entity_json = f"var entity = {json.dumps(entity)}"
            if case == "esterification" and postfix == "ideal":
                return render_template("home/model.html", entity=entity, entity_json=entity_json, model_context_json=model_context_json, pyomo=True, julia=True)
            else:
                return render_template("home/model.html", entity=entity, entity_json=entity_json, model_context_json=model_context_json, pyomo=False, julia=False)
    return render_template("home/page-404.html")




# TODO: Ask about the need for this route.
@blueprint.route("/model_export", methods=["POST"])
def model_export():
    entity = g.graphdb_handler.query()
    model_request = request.get_json()
    model_type = model_request["model_type"]
    model_context = model_request["model_context"]
    calibrated_parameter = model_request.get("calibrated_parameter")
    model_agent = ModelAgent(entity, model_context, calibrated_parameter)
    if model_type == "scipy":
        model = model_agent.to_scipy_model()
    elif model_type == "pyomo":
        model = model_agent.to_pyomo_model()
    elif model_type == "julia":
        model = model_agent.to_julia_model()
    else:
        model = ""
    buffer = BytesIO()
    buffer.write(model.encode("utf-8"))
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name="model",
        mimetype="text/plain"
    )


@blueprint.route("/model_structure", methods=["POST"])
def model_structure():
    entity = g.graphdb_handler.query(mode="mainpage")
    model_context = request.get_json()
    model_agent = ModelAgent(entity, model_context)
    flowchart = model_agent.to_flowchart()
    return jsonify(flowchart)


@blueprint.route("/model_simulation", methods=["POST"])
def model_simulation():
    entity = g.graphdb_handler.query()
    model_simulation_request = request.get_json()
    model_simulation_agent = ModelSimulationAgent(entity, model_simulation_request)
    results = model_simulation_agent.simulate_scipy()
    return results


@blueprint.route("/model_calibration", methods=["POST"])
def model_calibration():
    entity = g.graphdb_handler.query()
    model_calibration_request = request.get_json()
    model_calibration_agent = ModelCalibrationAgent(entity, model_calibration_request)
    result = model_calibration_agent.calibration_scipy()
    return result


@blueprint.route("/model_exploration", methods=["POST"])
def model_exploration():
    entity = g.graphdb_handler.query()
    model_exploration_request = request.get_json()
    model_exploration_agent = ModelExplorationAgent(entity, model_exploration_request)
    result = model_exploration_agent.exploration_scipy()
    return result