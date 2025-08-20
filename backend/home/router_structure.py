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

@blueprint.route("/structure")
def structure():
    entity = g.graphdb_handler.query(mode="sidebar")
    entity_json = f"var entity = {json.dumps(entity)}"
    return render_template("home/structure.html", entity=entity, entity_json=entity_json)


@blueprint.route("/structure/<path:case>")
def structure_case(case):
    cases_dir = Path(current_app.root_path) / "cases"
    cases = [c for c in os.listdir(cases_dir) if not c.startswith(".")]
    if case and case in cases:
        # Hardcoded parameter
        context_file = cases_dir / case / "model_context.json"
        if os.path.exists(context_file):
            model_context_json = f"var modelContext = {json.dumps(json.load(open(context_file, 'r')))}\n" + \
                                 "sessionStorage.setItem('modelContext', JSON.stringify(modelContext));"
            entity = g.graphdb_handler.query(mode="sidebar")
            entity_json = f"var entity = {json.dumps(entity)}"
            return render_template("home/structure.html", entity=entity, entity_json=entity_json, model_context_json=model_context_json)
    return render_template("home/page-404.html")
