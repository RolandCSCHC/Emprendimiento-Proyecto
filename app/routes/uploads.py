from __future__ import annotations

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for

from app.form_context import class_form_context
from app.services.programa_service import (
    ProgramaValidationError,
    create_programa,
    get_programa,
    list_programas,
)
from app.services.upload_service import (
    UploadValidationError,
    create_pending_session,
    finalize_class_upload,
)

uploads_bp = Blueprint("uploads", __name__)


@uploads_bp.route("/upload/programa", methods=["GET", "POST"])
def upload_programa():
    if request.method == "GET":
        return render_template("upload_programa.html", **class_form_context())

    nombre = request.form.get("nombre", "")
    gimnasio_id = request.form.get("gimnasio_id", "")
    profesor_id = request.form.get("profesor_id", "")
    tipo_clase_id = request.form.get("tipo_clase_id", "")
    sala = request.form.get("sala", "")
    nivel = request.form.get("nivel", "")

    form_data = class_form_context(
        nombre=nombre,
        gimnasio_id=gimnasio_id,
        profesor_id=profesor_id,
        tipo_clase_id=tipo_clase_id,
        sala=sala,
        nivel=nivel,
    )

    try:
        programa = create_programa(
            nombre=nombre,
            gimnasio_id=gimnasio_id,
            profesor_id=profesor_id,
            tipo_clase_id=tipo_clase_id,
            sala=sala,
            nivel=nivel,
        )
        flash("Clase creada correctamente. Ahora puedes subir la primera sesión.", "success")
        return redirect(url_for("dashboard.programa_detail", programa_id=programa.id))
    except ProgramaValidationError as exc:
        flash(str(exc), "error")
        return render_template("upload_programa.html", **form_data), 400


@uploads_bp.route("/upload", methods=["GET"])
@uploads_bp.route("/upload/programas/<programa_id>/sesion", methods=["GET"])
def upload(programa_id: str | None = None):
    programas = list_programas()
    programa = get_programa(programa_id) if programa_id else None
    if programa_id and programa is None:
        flash("Clase no encontrada.", "error")
        return redirect(url_for("uploads.upload"))

    return render_template(
        "upload.html",
        programas=programas,
        programa=programa,
        programa_id=str(programa.id) if programa else "",
        fecha="",
    )


@uploads_bp.route("/upload/create-pending", methods=["POST"])
def create_pending():
    origin = request.headers.get("Origin", "")
    if origin not in current_app.config["ALLOWED_ORIGINS"]:
        return jsonify({"error": "Origen no permitido."}), 403

    if not current_app.config["AWS_ENABLED"]:
        return jsonify({"error": "AWS no está habilitado."}), 503

    body = request.get_json(silent=True) or {}
    try:
        result = create_pending_session(
            programa_id=body.get("programa_id", ""),
            fecha=body.get("fecha", ""),
            video_filename=body.get("video_filename"),
            audio_filename=body.get("audio_filename"),
        )
        return jsonify(result), 201
    except UploadValidationError as exc:
        return jsonify({"error": str(exc)}), 400


@uploads_bp.route("/upload/<clase_id>/complete", methods=["POST"])
def upload_complete(clase_id: str):
    origin = request.headers.get("Origin", "")
    if origin not in current_app.config["ALLOWED_ORIGINS"]:
        return jsonify({"error": "Origen no permitido."}), 403

    if not current_app.config["AWS_ENABLED"]:
        return jsonify({"error": "AWS no está habilitado."}), 503

    try:
        clase = finalize_class_upload(clase_id)
        return jsonify({
            "clase_id": clase_id,
            "status": clase.status,
            "redirect_url": url_for("dashboard.session_detail", clase_id=clase_id),
        }), 200
    except UploadValidationError as exc:
        return jsonify({"error": str(exc)}), 400
