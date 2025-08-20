import os
import jwt
import requests
import datetime

from dotenv import load_dotenv
from flask import Flask, g, request, redirect, url_for, session, jsonify, current_app, make_response
from functools import wraps
from importlib import import_module
from .utils.graphdb_handler import GraphdbHandler

APP_PREFIX = os.environ.get("APP_PREFIX")
graphdb_handler_instance = None
load_dotenv()

def register_blueprint(app):
    for module_name in ["home"]:
        module = import_module(f"backend.{module_name}.routes")
        app.register_blueprint(module.blueprint)

def register_extension(app):
    # Initialize any additional extensions if needed.
    pass

# Setup Flask App with Frontend and Backend
def create_app(config):
    print("[Init] Flask app initialized with config: ", APP_PREFIX)
    if APP_PREFIX:
        app = Flask(__name__, static_url_path=f"/{APP_PREFIX}/static")
    else:
        app = Flask(__name__, static_url_path="/static")

    register_extension(app)
    register_blueprint(app)
    
    # Configure database
    # graphdb_handler = GraphdbHandler(config)

    @app.before_request
    def before_request():
        global graphdb_handler_instance

        if (APP_PREFIX and request.path == f"/{APP_PREFIX}/health") or request.path == "/health":
            return  # Bypass auth and allow health checks

        if graphdb_handler_instance is None:
            try:
                graphdb_handler_instance = GraphdbHandler(config)
                print("[Init] GraphDB handler initialized successfully.")
            except Exception as e:
                print(f"[Init] GraphDB handler failed to initialize: {e}")
                return make_response(f"GraphDB handler failed to initialize: {e}. Service temporarily unavailable. GraphDB not ready.", 503)

        g.graphdb_handler = graphdb_handler_instance
    
    @app.teardown_request
    def teardown_request(exception):
        handler = g.get("graphdb_handler", None)
        if handler:
            handler.close()

    return app