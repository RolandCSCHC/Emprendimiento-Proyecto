from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.services.class_service import list_gimnasios, list_profesores, list_tipos_clase
from app.services.upload_service import UploadValidationError, create_class_session

uploads_bp = Blueprint("uploads", __name__)


def _upload_form_context(**kwargs):
    gimnasios = list_gimnasios()
    gimnasio_id = kwargs.get("gimnasio_id") or (str(gimnasios[0].id) if gimnasios else "")
    return {
        "gimnasios": gimnasios,
        "profesores": list_profesores(),
        "tipos_clase": list_tipos_clase(),
        **kwargs,
        "gimnasio_id": gimnasio_id,
    }


@uploads_bp.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "GET":
        return render_template("upload.html", **_upload_form_context())

    nombre = request.form.get("nombre", "")
    fecha = request.form.get("fecha", "")
    gimnasio_id = request.form.get("gimnasio_id", "")
    profesor_id = request.form.get("profesor_id", "")
    tipo_clase_id = request.form.get("tipo_clase_id", "")
    sala = request.form.get("sala", "")
    nivel = request.form.get("nivel", "")
    video = request.files.get("video")
    audio = request.files.get("audio")

    form_data = _upload_form_context(
        nombre=nombre,
        fecha=fecha,
        gimnasio_id=gimnasio_id,
        profesor_id=profesor_id,
        tipo_clase_id=tipo_clase_id,
        sala=sala,
        nivel=nivel,
    )

    try:
        clase = create_class_session(
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
        flash("Clase creada correctamente. El análisis está pendiente.", "success")
        return redirect(url_for("dashboard.session_detail", clase_id=str(clase.id)))
    except UploadValidationError as exc:
        flash(str(exc), "error")
        return render_template("upload.html", **form_data), 400
