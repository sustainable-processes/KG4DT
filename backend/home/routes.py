import os
import json

from io import BytesIO
from pathlib import Path
from flask import (g, jsonify, render_template, request, send_file,
                   send_from_directory, session, url_for, current_app, redirect, flash)
from . import blueprint
from . import router_api
from . import router_model
from . import router_structure
from . import router_application
from . import router_knowledge_graph

from ..utils.model_agent import ModelAgent
from ..utils.model_calibration_agent import ModelCalibrationAgent
from ..utils.model_chatgpt_agent import ModelChatGPTAgent
from ..utils.model_exploration_agent import ModelExplorationAgent
from ..utils.model_simulation_agent import ModelSimulationAgent
from ..utils.physical_property_agent import PhysicalPropertyAgent
from ..utils.rule_inference_agent import RuleInferenceAgent
from ..utils.solute_solubility_agent import SoluteSolubilityAgent
from ..utils.solvent_miscibility_agent import SolventMiscibilityAgent


@blueprint.route("/health")
def health():
    return "OK", 200

@blueprint.route("/index")
def index():
    entity = g.graphdb_handler.query(mode="sidebar")
    entity_json = f"var entity = {json.dumps(entity)}"
    return render_template("home/index.html", entity=entity, entity_json=entity_json)


@blueprint.route("/chatgpt")
def chatgpt():
    entity = g.graphdb_handler.query(mode="sidebar")
    entity_json = f"var entity = {json.dumps(entity)}"
    return render_template("home/chatgpt.html", entity=entity, entity_json=entity_json)


@blueprint.route("/openai", methods=["POST"])
def openai():
    entity = g.graphdb_handler.query(mode="mainpage")
    model_chatgpt_request = request.get_json()
    model_chatgpt_agent = ModelChatGPTAgent(entity, model_chatgpt_request)
    return model_chatgpt_agent.query()


@blueprint.route("/solvent_miscibility_table")
def solvent_miscibility_table():
    entity = g.graphdb_handler.query()
    return render_template("home/solvent_miscibility_table.html", entity=entity)


@blueprint.route("/physical_property_pubchem", methods=["POST"])
def physical_property_pubchem():
    entity = g.graphdb_handler.query()
    physical_property_agent = PhysicalPropertyAgent(entity)
    solvents = request.get_json()
    physical_property = physical_property_agent.query_pubchem(solvents, ["Density", "Viscosity"])
    return physical_property


@blueprint.route("/physical_property_chemspider", methods=["POST"])
def physical_property_chemspider():
    entity = g.graphdb_handler.query()
    physical_property_agent = PhysicalPropertyAgent(entity)
    solvents = request.get_json()
    physical_property = physical_property_agent.query_chemspider(solvents, ["Density"])
    return physical_property


@blueprint.route("/physical_property_wikipedia", methods=["POST"])
def physical_property_wikipedia():
    entity = g.graphdb_handler.query()
    physical_property_agent = PhysicalPropertyAgent(entity)
    solvents = request.get_json()
    physical_property = physical_property_agent.query_wikipedia(solvents, ["Density", "Viscosity"])
    return physical_property


@blueprint.route("/solvent_miscibility", methods=["POST"])
def solvent_miscibility():
    entity = g.graphdb_handler.query()
    data_path = Path(current_app.root_path) / "data" / "solvent_miscibility_table.csv"
    solvent_miscibility_agent = SolventMiscibilityAgent(entity, str(data_path))
    solvents = request.get_json()
    return solvent_miscibility_agent.query_sigmaaldrich(solvents)


@blueprint.route("/solute_solubility", methods=["POST"])
def solute_solubility():
    entity = g.graphdb_handler.query()
    solute_solubility_agent = SoluteSolubilityAgent(entity)
    solution = request.get_json()
    return solute_solubility_agent.query_rmg(solution)


@blueprint.route("/rule_inference", methods=["POST"])
def rule_inference():
    entity = g.graphdb_handler.query()
    rule_inference_request = request.get_json()
    rule_inference_agent = RuleInferenceAgent(entity, g.graphdb_handler)
    return rule_inference_agent.infer(rule_inference_request["data"])


@blueprint.route("/cases/<path:filepath>")
def case_file(filepath):
    folder = os.path.join(current_app.root_path, "cases", os.path.dirname(filepath))
    file_name = os.path.basename(filepath)
    return send_from_directory(folder, file_name)