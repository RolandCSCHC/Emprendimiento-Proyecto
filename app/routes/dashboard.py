from __future__ import annotations

import uuid

from flask import Blueprint, abort, current_app, render_template

from app.services.class_service import get_clase, list_clases

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


def _status_label(status: str) -> str:
    labels = {
        "pendiente_analisis": "Pendiente de análisis",
        "analizando": "Analizando",
        "completada": "Completada",
        "error": "Error",
    }
    return labels.get(status, status)


@dashboard_bp.route("/")
def dashboard():
    clases = list_clases()
    return render_template("dashboard.html", clases=clases)


@dashboard_bp.route("/<clase_id>")
def session_detail(clase_id: str):
    try:
        uuid.UUID(clase_id)
    except ValueError:
        abort(404)

    clase = get_clase(clase_id)
    if clase is None:
        abort(404)

    metric_labels = current_app.config["METRIC_LABELS"]
    metricas_by_key = {m.clave: m for m in clase.metricas}
    metrics = [
        {
            "key": key,
            "label": metric_labels.get(key, key),
            "metrica": metricas_by_key.get(key),
        }
        for key in current_app.config["METRIC_KEYS"]
    ]

    return render_template(
        "session_detail.html",
        clase=clase,
        metrics=metrics,
        status_label=_status_label(clase.status),
    )
