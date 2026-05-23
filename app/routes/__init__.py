from flask import Flask

from app.routes.dashboard import dashboard_bp
from app.routes.main import main_bp
from app.routes.uploads import uploads_bp


def register_blueprints(flask_app: Flask) -> None:
    flask_app.register_blueprint(main_bp)
    flask_app.register_blueprint(uploads_bp)
    flask_app.register_blueprint(dashboard_bp)
