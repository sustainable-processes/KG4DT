from flask import Blueprint
import os

APP_PREFIX = os.environ.get("APP_PREFIX")

if APP_PREFIX:
    blueprint = Blueprint("home", __name__, url_prefix=f"/{APP_PREFIX}")
else:
    blueprint = Blueprint("home", __name__)