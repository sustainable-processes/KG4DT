from flask import Flask, g
from importlib import import_module
from .utils.graphdb_handler import GraphdbHandler


def register_extension(app):
    pass


def register_blueprint(app):
    for module_name in ["home"]:
        module = import_module(f"app.{module_name}.routes")
        app.register_blueprint(module.blueprint)


def create_app(config):
    app = Flask(__name__)
    app.config.from_object(config)

    # Initialize Flask extensions

    # Register blueprints
    register_blueprint(app)
    
    # Configure database
    graphdb_handler = GraphdbHandler(config)

    @app.before_request
    def before_request():
        g.graphdb_handler = graphdb_handler
    
    @app.teardown_request
    def teardown_request(exception):
        g.graphdb_handler.close()

    return app