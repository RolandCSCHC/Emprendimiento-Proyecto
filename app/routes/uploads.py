from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.services.upload_service import UploadValidationError, create_class_session

uploads_bp = Blueprint("uploads", __name__)


@uploads_bp.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "GET":
        return render_template("upload.html")

    nombre = request.form.get("nombre", "")
    fecha = request.form.get("fecha", "")
    video = request.files.get("video")
    audio = request.files.get("audio")

    try:
        session = create_class_session(nombre=nombre, fecha=fecha, video=video, audio=audio)
        flash("Clase creada correctamente. El análisis está pendiente.", "success")
        return redirect(url_for("dashboard.session_detail", session_id=session.id))
    except UploadValidationError as exc:
        flash(str(exc), "error")
        return render_template("upload.html", nombre=nombre, fecha=fecha), 400
