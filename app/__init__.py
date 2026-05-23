from __future__ import annotations

import os

from flask import Flask
from dotenv import load_dotenv

from app.config import config_by_name


def create_app(config_name: str | None = None) -> Flask:
    load_dotenv()

    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name["development"]))

    app.config["UPLOAD_FOLDER"].mkdir(parents=True, exist_ok=True)
    app.config["DATA_FOLDER"].mkdir(parents=True, exist_ok=True)

    from app.routes import register_blueprints

    register_blueprints(app)

    return app
