import json
import os
from io import BytesIO

from flask import (g, jsonify, render_template, request, send_file,
                   send_from_directory)

from app.home import blueprint
from app.utils.model_agent import ModelAgent
from app.utils.model_calibration_agent import ModelCalibrationAgent
from app.utils.model_chatgpt_agent import ModelChatGPTAgent
from app.utils.model_exploration_agent import ModelExplorationAgent
from app.utils.model_knowledge_graph_agent import ModelKnowledgeGraphAgent
from app.utils.model_simulation_agent import ModelSimulationAgent
from app.utils.physical_property_agent import PhysicalPropertyAgent
from app.utils.rule_inference_agent import RuleInferenceAgent
from app.utils.solute_solubility_agent import SoluteSolubilityAgent
from app.utils.solvent_miscibility_agent import SolventMiscibilityAgent


@blueprint.route("/index")
def index():
    entity = g.graphdb_handler.query(mode="sidebar")
    entity_json = f"var entity = {json.dumps(entity)}"
    return render_template("home/index.html", entity=entity, entity_json=entity_json)


@blueprint.route("/model")
def model():
    entity = g.graphdb_handler.query(mode="sidebar")
    entity_json = f"var entity = {json.dumps(entity)}"
    model_context_json = """
        if (sessionStorage.getItem('modelContext')) {
            var modelContext = JSON.parse(sessionStorage.getItem('modelContext'));
        };
    """
    return render_template("home/model.html", entity=entity, entity_json=entity_json, model_context_json=model_context_json)


@blueprint.route("/model/<path:case>")
def model_case(case):
    cases = [c for c in os.listdir('app/cases') if not c.startswith(".")]
    if case and case in cases:
        if os.path.exists('app/cases/' + case + '/model_context.json'):
            model_context_json = f"var modelContext = {json.dumps(json.load(open('app/cases/' + case + '/model_context.json', 'r')))}\n" + \
                                 "sessionStorage.removeItem('modelContext');"
            entity = g.graphdb_handler.query(mode="sidebar")
            entity_json = f"var entity = {json.dumps(entity)}"
            return render_template("home/model.html", entity=entity, entity_json=entity_json, model_context_json=model_context_json)
    return render_template("home/page-404.html")


@blueprint.route("/model/<path:case>/<path:postfix>")
def model_case_postfix(case, postfix):
    cases = [c for c in os.listdir('app/cases') if not c.startswith(".")]
    if case and case in cases:
        if f"model_context_{postfix}.json" in os.listdir(f'app/cases/{case}'):
            model_context_json = f"var modelContext = {json.dumps(json.load(open(f'app/cases/{case}/model_context_{postfix}.json', 'r')))}\n" + \
                                 "sessionStorage.removeItem('modelContext');"
            entity = g.graphdb_handler.query(mode="sidebar")
            entity_json = f"var entity = {json.dumps(entity)}"
            if case == "esterification" and postfix == "ideal":
                return render_template("home/model.html", entity=entity, entity_json=entity_json, model_context_json=model_context_json, pyomo=True, julia=True)
            else:
                return render_template("home/model.html", entity=entity, entity_json=entity_json, model_context_json=model_context_json, pyomo=False, julia=False)
    return render_template("home/page-404.html")


@blueprint.route("/structure")
def structure():
    entity = g.graphdb_handler.query(mode="sidebar")
    entity_json = f"var entity = {json.dumps(entity)}"
    return render_template("home/structure.html", entity=entity, entity_json=entity_json)


@blueprint.route("/structure/<path:case>")
def structure_case(case):
    cases = [c for c in os.listdir('app/cases') if not c.startswith(".")]
    if case and case in cases:
        if os.path.exists('app/cases/' + case + '/model_context.json'):
            model_context_json = f"var modelContext = {json.dumps(json.load(open('app/cases/' + case + '/model_context.json', 'r')))}\n" + \
                                 "sessionStorage.setItem('modelContext', JSON.stringify(modelContext));"
            entity = g.graphdb_handler.query(mode="sidebar")
            entity_json = f"var entity = {json.dumps(entity)}"
            return render_template("home/structure.html", entity=entity, entity_json=entity_json, model_context_json=model_context_json)
    return render_template("home/page-404.html")


@blueprint.route("/application")
def application():
    entity = g.graphdb_handler.query(mode="sidebar")
    entity_json = f"var entity = {json.dumps(entity)}"
    return render_template("home/application.html", entity=entity, entity_json=entity_json)


@blueprint.route("/application/<path:case>")
def application_case(case):
    cases = [c for c in os.listdir('app/cases') if not c.startswith(".")]
    if case and case in cases:
        if os.path.exists('app/cases/' + case + '/model_context.json'):
            model_context_json = f"var modelContext = {json.dumps(json.load(open('app/cases/' + case + '/model_context.json', 'r')))}\n" + \
                                 "sessionStorage.setItem('modelContext', JSON.stringify(modelContext));"
            entity = g.graphdb_handler.query(mode="sidebar")
            entity_json = f"var entity = {json.dumps(entity)}"
            return render_template("home/application.html", entity=entity, entity_json=entity_json, model_context_json=model_context_json)
    return render_template("home/page-404.html")


@blueprint.route("/knowledge_graph")
def knowledge_graph():
    entity = g.graphdb_handler.query(mode="sidebar")
    entity_mainpage = g.graphdb_handler.query(mode="mainpage")
    entity_json = f"var entity = {json.dumps(entity_mainpage)}"
    knowledge_graph_data = ModelKnowledgeGraphAgent(entity).to_knowledge_graph_data()
    knowledge_graph_data_json = f"var knowledgeGraphData = {json.dumps(knowledge_graph_data)}"
    model_context_json = """
        if (sessionStorage.getItem('modelContext')) {
            var modelContext = JSON.parse(sessionStorage.getItem('modelContext'));
        };
    """
    return render_template("home/knowledge_graph.html", entity=entity, entity_json=entity_json, model_context_json=model_context_json, knowledge_graph_data_json=knowledge_graph_data_json)


@blueprint.route("/knowledge_graph/<path:case>")
def knowledge_graph_case(case):
    cases = [c for c in os.listdir('app/cases') if not c.startswith(".")]
    if case and case in cases:
        entity = g.graphdb_handler.query(mode="sidebar")
        entity_mainpage = g.graphdb_handler.query(mode="mainpage")
        entity_json = f"var entity = {json.dumps(entity_mainpage)}"
        knowledge_graph_data = ModelKnowledgeGraphAgent(entity).to_knowledge_graph_data()
        knowledge_graph_data_json = f"var knowledgeGraphData = {json.dumps(knowledge_graph_data)}"
        model_context_json = f"var modelContext = {json.dumps(json.load(open('app/cases/' + case + '/top_down_rule_model_context.json', 'r')))}\n" + \
                             "sessionStorage.removeItem('modelContext');"
        return render_template("home/knowledge_graph.html", entity=entity, entity_json=entity_json, model_context_json=model_context_json, knowledge_graph_data_json=knowledge_graph_data_json)
    return render_template("home/page-404.html")


@blueprint.route("/exploration")
def exploration():
    entity = g.graphdb_handler.query(mode="sidebar")
    entity_json = f"var entity = {json.dumps(entity)}"
    model_context_json = """
        if (sessionStorage.getItem('modelContext')) {
            var modelContext = JSON.parse(sessionStorage.getItem('modelContext'));
        };
    """
    return render_template("home/exploration.html", entity=entity, entity_json=entity_json, model_context_json=model_context_json)


@blueprint.route("/exploration/<path:case>")
def exploration_case(case):
    cases = [c for c in os.listdir('app/cases') if not c.startswith(".")]
    if case and case in cases:
        entity = g.graphdb_handler.query(mode="sidebar")
        entity_json = f"var entity = {json.dumps(entity)}"
        if os.path.exists('app/cases/' + case + '/top_down_exploration_model_context.json'):
            model_context_json = f"var modelContext = {json.dumps(json.load(open('app/cases/' + case + '/top_down_exploration_model_context.json', 'r')))}\n" + \
                                "sessionStorage.removeItem('modelContext');"
            return render_template("home/exploration.html", entity=entity, entity_json=entity_json, model_context_json=model_context_json)
    return render_template("home/page-404.html")


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


@blueprint.route("/model_export", methods=["POST"])
def model_export():
    entity = g.graphdb_handler.query()
    model_request = request.get_json()
    model_type = model_request["model_type"]
    model_context = model_request["model_context"]
    if "calibrated_parameter" in model_request:
        calibrated_parameter = model_request["calibrated_parameter"]
    else:
        calibrated_parameter = None
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
    solvent_miscibility_agent = SolventMiscibilityAgent(entity, "app/data/solvent_miscibility_table.csv")
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
    folder = os.path.join("cases", os.path.dirname(filepath))
    file_name = os.path.basename(filepath)
    return send_from_directory(folder, file_name)