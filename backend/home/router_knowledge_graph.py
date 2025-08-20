import os
import json
from io import BytesIO
from pathlib import Path
from flask import (
    g, jsonify, render_template, request, send_file,
    current_app
)
from . import blueprint
from ..utils.model_knowledge_graph_agent import ModelKnowledgeGraphAgent


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
    cases_dir = Path(current_app.root_path) / "cases"
    cases = [c for c in os.listdir(cases_dir) if not c.startswith(".")]
    if case and case in cases:
        entity = g.graphdb_handler.query(mode="sidebar")
        entity_mainpage = g.graphdb_handler.query(mode="mainpage")
        entity_json = f"var entity = {json.dumps(entity_mainpage)}"
        knowledge_graph_data = ModelKnowledgeGraphAgent(entity).to_knowledge_graph_data()
        knowledge_graph_data_json = f"var knowledgeGraphData = {json.dumps(knowledge_graph_data)}"
        context_file = cases_dir / case / "top_down_rule_model_context.json"
        model_context_json = f"var modelContext = {json.dumps(json.load(open(context_file, 'r')))}\n" + \
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
    cases_dir = Path(current_app.root_path) / "cases"
    cases = [c for c in os.listdir(cases_dir) if not c.startswith(".")]
    if case and case in cases:
        entity = g.graphdb_handler.query(mode="sidebar")
        entity_json = f"var entity = {json.dumps(entity)}"
        context_file = cases_dir / case / "top_down_exploration_model_context.json"
        if os.path.exists(context_file):
            model_context_json = f"var modelContext = {json.dumps(json.load(open(context_file, 'r')))}\n" + \
                                "sessionStorage.removeItem('modelContext');"
            return render_template("home/exploration.html", entity=entity, entity_json=entity_json, model_context_json=model_context_json)
    return render_template("home/page-404.html")
