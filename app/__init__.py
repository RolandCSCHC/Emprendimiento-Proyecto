from __future__ import annotations

import os

from flask import Flask
from dotenv import load_dotenv

from app.config import config_by_name
from app.extensions import db, migrate


def create_app(config_name: str | None = None) -> Flask:
    load_dotenv()

    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    flask_app = Flask(__name__)
    flask_app.config.from_object(
        config_by_name.get(config_name, config_by_name["development"])
    )

    flask_app.config["UPLOAD_FOLDER"].mkdir(parents=True, exist_ok=True)

    db.init_app(flask_app)
    migrate.init_app(flask_app, db)

    import app.models as _models  # noqa: F401

    from app.routes import register_blueprints

    register_blueprints(flask_app)
    register_cli(flask_app)

    return flask_app


def register_cli(flask_app: Flask) -> None:
    @flask_app.cli.command("init-db")
    def init_db_command():
        """Crea tablas y datos iniciales de demostración."""
        from app.seed import seed_database

        db.create_all()
        seed_database()
        print("Base de datos inicializada.")

    @flask_app.cli.command("seed")
    def seed_command():
        """Inserta datos de demostración si no existen."""
        from app.seed import seed_database

        seed_database()
        print("Seed completado.")

    @flask_app.cli.command("aws-poll-jobs")
    def aws_poll_jobs_command():
        """Consulta jobs de análisis AWS pendientes (cuando esté implementado)."""
        from app.services.analysis_service import poll_pending_jobs

        try:
            count = poll_pending_jobs()
            print(f"Jobs procesados: {count}")
        except NotImplementedError as exc:
            print(exc)
