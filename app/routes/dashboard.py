from __future__ import annotations

import uuid

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from app.form_context import class_form_context
from app.services.class_service import delete_clase, get_clase
from app.services.programa_service import (
    chart_point_count,
    delete_programa,
    get_programa,
    get_programa_metric_series,
    list_programas,
    list_sesiones,
)
from app.services.upload_service import UploadValidationError, update_class_session

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


def _status_label(status: str) -> str:
    labels = {
        "awaiting_upload": "Esperando subida",
        "pendiente_analisis": "Pendiente de análisis",
        "analizando": "Analizando",
        "completada": "Completada",
        "completada_parcial": "Completada parcial",
        "error": "Error",
    }
    return labels.get(status, status)


def _get_clase_or_404(clase_id: str):
    try:
        uuid.UUID(clase_id)
    except ValueError:
        abort(404)

    clase = get_clase(clase_id)
    if clase is None:
        abort(404)
    return clase


def _get_programa_or_404(programa_id: str):
    try:
        uuid.UUID(programa_id)
    except ValueError:
        abort(404)

    programa = get_programa(programa_id)
    if programa is None:
        abort(404)
    return programa


def _fecha_input_value(clase) -> str:
    fecha = clase.fecha_inicio
    if fecha.tzinfo is not None:
        fecha = fecha.replace(tzinfo=None)
    return fecha.strftime("%Y-%m-%dT%H:%M")


@dashboard_bp.route("/")
def dashboard():
    programas = list_programas()
    return render_template(
        "dashboard.html",
        programas=programas,
        status_label=_status_label,
    )


@dashboard_bp.route("/programas/<programa_id>")
def programa_detail(programa_id: str):
    programa = _get_programa_or_404(programa_id)
    sesiones = list_sesiones(programa_id)
    chart_series = get_programa_metric_series(programa_id)
    return render_template(
        "programa_detail.html",
        programa=programa,
        sesiones=sesiones,
        status_label=_status_label,
        chart_series=chart_series,
        chart_point_count=chart_point_count(chart_series),
        metric_keys=current_app.config["METRIC_KEYS"],
        metric_labels=current_app.config["METRIC_LABELS"],
    )


@dashboard_bp.route("/programas/<programa_id>/delete", methods=["POST"])
def delete_programa_route(programa_id: str):
    _get_programa_or_404(programa_id)

    if delete_programa(programa_id):
        flash("Clase eliminada correctamente.", "success")
    else:
        flash("No se pudo eliminar la clase.", "error")

    return redirect(url_for("dashboard.dashboard"))


@dashboard_bp.route("/<clase_id>/edit", methods=["GET", "POST"])
def edit_clase(clase_id: str):
    clase = _get_clase_or_404(clase_id)

    if request.method == "GET":
        return render_template(
            "edit.html",
            clase=clase,
            **class_form_context(
                nombre=clase.nombre,
                fecha=_fecha_input_value(clase),
                gimnasio_id=str(clase.gimnasio_id),
                profesor_id=str(clase.profesor_id),
                tipo_clase_id=str(clase.tipo_clase_id),
                sala=clase.sala or "",
                nivel=clase.nivel or "",
            ),
        )

    nombre = request.form.get("nombre", "")
    fecha = request.form.get("fecha", "")
    gimnasio_id = request.form.get("gimnasio_id", "")
    profesor_id = request.form.get("profesor_id", "")
    tipo_clase_id = request.form.get("tipo_clase_id", "")
    sala = request.form.get("sala", "")
    nivel = request.form.get("nivel", "")
    video = request.files.get("video")
    audio = request.files.get("audio")

    form_data = class_form_context(
        nombre=nombre,
        fecha=fecha,
        gimnasio_id=gimnasio_id,
        profesor_id=profesor_id,
        tipo_clase_id=tipo_clase_id,
        sala=sala,
        nivel=nivel,
    )

    try:
        update_class_session(
            clase_id=clase_id,
            nombre=nombre,
            fecha=fecha,
            gimnasio_id=gimnasio_id,
            profesor_id=profesor_id,
            tipo_clase_id=tipo_clase_id,
            video=video,
            audio=audio,
            sala=sala,
            nivel=nivel,
        )
        flash("Sesión actualizada correctamente.", "success")
        return redirect(url_for("dashboard.session_detail", clase_id=clase_id))
    except UploadValidationError as exc:
        flash(str(exc), "error")
        return render_template("edit.html", clase=clase, **form_data), 400


@dashboard_bp.route("/<clase_id>/delete", methods=["POST"])
def delete_clase_route(clase_id: str):
    clase = _get_clase_or_404(clase_id)
    programa_id = clase.programa_id

    if delete_clase(clase_id):
        flash("Sesión eliminada correctamente.", "success")
    else:
        flash("No se pudo eliminar la sesión.", "error")

    return redirect(url_for("dashboard.programa_detail", programa_id=programa_id))


@dashboard_bp.route("/<clase_id>")
def session_detail(clase_id: str):
    clase = _get_clase_or_404(clase_id)

    from app.metric_display import format_metric_value

    metric_labels = current_app.config["METRIC_LABELS"]
    metricas_by_key = {m.clave: m for m in clase.metricas}
    metrics = []
    for key in current_app.config["METRIC_KEYS"]:
        metrica = metricas_by_key.get(key)
        display_value = None
        if metrica and metrica.status == "completed":
            if metrica.valor_numerico is not None:
                display_value = format_metric_value(
                    key, metrica.valor_numerico, metrica.unidad
                )
            elif metrica.valor_texto:
                display_value = metrica.valor_texto
        metrics.append(
            {
                "key": key,
                "label": metric_labels.get(key, key),
                "metrica": metrica,
                "display_value": display_value,
            }
        )

    return render_template(
        "session_detail.html",
        clase=clase,
        metrics=metrics,
        status_label=_status_label(clase.status),
    )
