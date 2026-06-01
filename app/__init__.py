from __future__ import annotations

import os

import click
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

    _validate_aws_config(flask_app)

    db.init_app(flask_app)
    migrate.init_app(flask_app, db)

    import app.models as _models  # noqa: F401

    from app.routes import register_blueprints

    register_blueprints(flask_app)
    register_cli(flask_app)
    register_template_filters(flask_app)

    return flask_app


def register_template_filters(flask_app: Flask) -> None:
    from app.metric_display import format_metric_value

    flask_app.jinja_env.filters["format_metric"] = format_metric_value


def _validate_aws_config(flask_app: Flask) -> None:
    """
    Si AWS está habilitado pero falta configuración requerida (AWS_REGION o
    S3_BUCKET), loguea un error y deshabilita el pipeline automáticamente
    para que la app siga funcionando (requisito 14.3).
    """
    if not flask_app.config.get("AWS_ENABLED"):
        return

    faltantes = [
        nombre
        for nombre in ("AWS_REGION", "S3_BUCKET")
        if not flask_app.config.get(nombre)
    ]
    if faltantes:
        flask_app.logger.error(
            "AWS_ENABLED=true pero falta(n) %s. Se deshabilita el pipeline AWS.",
            ", ".join(faltantes),
        )
        flask_app.config["AWS_ENABLED"] = False


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

    @flask_app.cli.command("aws-analyze")
    @click.argument("clase_id", required=False)
    def aws_analyze_command(clase_id):
        """Encola el análisis AWS de una clase, o de todas las pendientes si no se pasa id."""
        from app.models import Clase
        from app.services.analysis_service import enqueue_analysis

        if not flask_app.config.get("AWS_ENABLED"):
            print("AWS_ENABLED=false: no se encoló nada. Activa AWS en el .env.")
            return

        if clase_id:
            enqueue_analysis(clase_id)
            print(f"Análisis encolado para la clase {clase_id}.")
            return

        clases = Clase.query.filter_by(status="pendiente_analisis").all()
        for clase in clases:
            enqueue_analysis(str(clase.id))
        print(f"Análisis encolado para {len(clases)} clase(s) pendiente(s).")

    @flask_app.cli.command("aws-poll-jobs")
    def aws_poll_jobs_command():
        """Consulta jobs de análisis AWS pendientes (cuando esté implementado)."""
        from app.services.analysis_service import poll_pending_jobs

        try:
            count = poll_pending_jobs()
            print(f"Jobs procesados: {count}")
        except NotImplementedError as exc:
            print(exc)
