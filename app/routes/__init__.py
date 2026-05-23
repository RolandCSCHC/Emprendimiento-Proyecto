from flask import Flask

from app.routes.dashboard import dashboard_bp
from app.routes.main import main_bp
from app.routes.uploads import uploads_bp


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(main_bp)
    app.register_blueprint(uploads_bp)
    app.register_blueprint(dashboard_bp)
