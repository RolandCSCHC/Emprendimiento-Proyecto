from __future__ import annotations

from flask import Blueprint, current_app, jsonify, render_template, request, url_for

from app.form_context import class_form_context
from app.services.upload_service import (
    UploadValidationError,
    create_pending_class,
    finalize_class_upload,
)

uploads_bp = Blueprint("uploads", __name__)


@uploads_bp.route("/upload", methods=["GET"])
def upload():
    return render_template("upload.html", **class_form_context())


@uploads_bp.route("/upload/create-pending", methods=["POST"])
def create_pending():
    origin = request.headers.get("Origin", "")
    if origin not in current_app.config["ALLOWED_ORIGINS"]:
        return jsonify({"error": "Origen no permitido."}), 403

    if not current_app.config["AWS_ENABLED"]:
        return jsonify({"error": "AWS no está habilitado."}), 503

    body = request.get_json(silent=True) or {}
    try:
        result = create_pending_class(
            nombre=body.get("nombre", ""),
            fecha=body.get("fecha", ""),
            gimnasio_id=body.get("gimnasio_id", ""),
            profesor_id=body.get("profesor_id", ""),
            tipo_clase_id=body.get("tipo_clase_id", ""),
            sala=body.get("sala"),
            nivel=body.get("nivel"),
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
