import os
import requests
import datetime

from dotenv import load_dotenv
from flask import Flask, g, request, redirect, url_for, session, jsonify, current_app, make_response
from functools import wraps
from importlib import import_module
from .utils.graphdb_handler import GraphdbHandler

# Load environment variables before accessing them
load_dotenv()
APP_PREFIX = os.environ.get("APP_PREFIX")

graphdb_handler_instance = None

def register_blueprint(app):
    for module_name in ["home"]:
        module = import_module(f"backend.{module_name}.routes")
        app.register_blueprint(module.blueprint)

def register_extension(app):
    # Initialize any additional extensions if needed.
    # Initialize SQLAlchemy models/engine
    try:
        from . import models
        models.init_app(app)
        print("[Init] Database models initialized.")
    except Exception as e:
        print(f"[Init] Database init failed: {e}")
        # Defer failure to first use; app can still start without DB.
        # Alternatively, re-raise to make DB mandatory.
        # raise
        pass

# Setup Flask App with Frontend and Backend
def create_app(config):
    print(f"[Init] Flask app initialized with APP_PREFIX={APP_PREFIX}, config={config}")
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

        # Allow health checks without any special handling
        if (APP_PREFIX and request.path == f"/{APP_PREFIX}/health") or request.path == "/health":
            return

        # If APP_PREFIX is set, transparently redirect bare /api/* calls to the prefixed path.
        # Use 307 to preserve the HTTP method for POST/PUT/PATCH.
        if APP_PREFIX and request.path.startswith("/api/"):
            target = f"/{APP_PREFIX}{request.full_path}" if request.query_string else f"/{APP_PREFIX}{request.path}"
            # full_path already includes '?' if query_string present
            return redirect(target, code=307)

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
        # We don't close the graphdb_handler_instance here because it's a global singleton
        # intended to last for the lifetime of the application process.
        pass

    return app