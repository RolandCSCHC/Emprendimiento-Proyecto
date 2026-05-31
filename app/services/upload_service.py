from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from flask import current_app, url_for

from app.extensions import db
from app.models import AnalisisJob, ArchivoMedia, Clase
from app.services.analysis_service import enqueue_analysis
from app.services.class_service import (
    create_pending_analysis_jobs,
    create_pending_metrics,
    get_clase,
)
from app.services.aws import s3_client


class UploadValidationError(Exception):
    pass


def _allowed_file(filename: str, allowed: set[str]) -> bool:
    if "." not in filename:
        return False
    extension = filename.rsplit(".", 1)[1].lower()
    return extension in allowed


def _parse_fecha(fecha_str: str) -> datetime:
    if not fecha_str.strip():
        raise UploadValidationError("La fecha de la clase es obligatoria.")
    try:
        return datetime.fromisoformat(fecha_str)
    except ValueError as exc:
        raise UploadValidationError("Formato de fecha inválido.") from exc


def _save_file(clase_id: uuid.UUID, file: FileStorage, prefix: str) -> ArchivoMedia:
    original = secure_filename(file.filename or "")
    extension = original.rsplit(".", 1)[1].lower()
    filename = f"{prefix}.{extension}"
    clase_dir = current_app.config["UPLOAD_FOLDER"] / str(clase_id)
    clase_dir.mkdir(parents=True, exist_ok=True)
    destination = clase_dir / filename
    file.save(destination)
    tamano = destination.stat().st_size

    tipo = "video" if prefix == "video" else "audio"
    return ArchivoMedia(
        tipo=tipo,
        nombre_original=original,
        extension=extension,
        ruta_local=str(Path(str(clase_id)) / filename),
        tamano_bytes=tamano,
        mime_type=file.mimetype,
    )


def _remove_archivos_por_tipo(clase: Clase, tipo: str) -> None:
    upload_root = current_app.config["UPLOAD_FOLDER"]
    for archivo in list(clase.archivos):
        if archivo.tipo != tipo:
            continue
        for job in list(clase.analisis_jobs):
            if job.archivo_media_id == archivo.id:
                db.session.delete(job)
        if archivo.ruta_local:
            file_path = upload_root / archivo.ruta_local
            if file_path.exists():
                file_path.unlink()
        db.session.delete(archivo)


def update_class_session(
    clase_id: str,
    nombre: str,
    fecha: str,
    gimnasio_id: str,
    profesor_id: str,
    tipo_clase_id: str,
    video: FileStorage | None,
    audio: FileStorage | None,
    sala: str | None = None,
    nivel: str | None = None,
) -> Clase:
    clase = get_clase(clase_id)
    if clase is None:
        raise UploadValidationError("Clase no encontrada.")

    if not nombre.strip():
        raise UploadValidationError("El nombre de la clase es obligatorio.")

    has_video = video and video.filename
    has_audio = audio and audio.filename

    if has_video and not _allowed_file(
        video.filename, current_app.config["ALLOWED_VIDEO_EXTENSIONS"]
    ):
        raise UploadValidationError(
            "Formato de video no permitido. Usa: mp4, webm o mov."
        )

    if has_audio and not _allowed_file(
        audio.filename, current_app.config["ALLOWED_AUDIO_EXTENSIONS"]
    ):
        raise UploadValidationError(
            "Formato de audio no permitido. Usa: mp3, wav, m4a u ogg."
        )

    try:
        gimnasio_uuid = uuid.UUID(gimnasio_id)
        profesor_uuid = uuid.UUID(profesor_id)
        tipo_clase_uuid = uuid.UUID(tipo_clase_id)
    except ValueError as exc:
        raise UploadValidationError("Selecciona gimnasio, profesor y tipo de clase válidos.") from exc

    fecha_inicio = _parse_fecha(fecha)

    clase.gimnasio_id = gimnasio_uuid
    clase.profesor_id = profesor_uuid
    clase.tipo_clase_id = tipo_clase_uuid
    clase.nombre = nombre.strip()
    clase.fecha_inicio = fecha_inicio
    clase.sala = sala.strip() if sala else None
    clase.nivel = nivel.strip() if nivel else None

    if has_video:
        _remove_archivos_por_tipo(clase, "video")
        clase.archivos.append(_save_file(clase.id, video, "video"))

    if has_audio:
        _remove_archivos_por_tipo(clase, "audio")
        clase.archivos.append(_save_file(clase.id, audio, "audio"))

    if not clase.archivos:
        raise UploadValidationError("La clase debe tener al menos un archivo de video o audio.")

    db.session.flush()

    existing_job_archivo_ids = {
        job.archivo_media_id for job in clase.analisis_jobs if job.archivo_media_id
    }
    for archivo in clase.archivos:
        if archivo.id not in existing_job_archivo_ids:
            servicio = "rekognition" if archivo.tipo == "video" else "transcribe"
            db.session.add(
                AnalisisJob(
                    clase=clase,
                    archivo=archivo,
                    servicio=servicio,
                    status="pending",
                )
            )

    db.session.commit()

    if has_video or has_audio:
        enqueue_analysis(str(clase.id))

    return clase


def create_pending_class(
    *,
    nombre: str,
    fecha: str,
    gimnasio_id: str,
    profesor_id: str,
    tipo_clase_id: str,
    sala: str | None = None,
    nivel: str | None = None,
    video_filename: str | None = None,
    audio_filename: str | None = None,
) -> dict:
    if not nombre.strip():
        raise UploadValidationError("El nombre de la clase es obligatorio.")

    if not video_filename and not audio_filename:
        raise UploadValidationError("Debes subir al menos un archivo de video o audio.")

    if video_filename and not _allowed_file(
        video_filename, current_app.config["ALLOWED_VIDEO_EXTENSIONS"]
    ):
        raise UploadValidationError(
            "Formato de video no permitido. Usa: mp4, webm o mov."
        )

    if audio_filename and not _allowed_file(
        audio_filename, current_app.config["ALLOWED_AUDIO_EXTENSIONS"]
    ):
        raise UploadValidationError(
            "Formato de audio no permitido. Usa: mp3, wav, m4a u ogg."
        )

    try:
        gimnasio_uuid = uuid.UUID(gimnasio_id)
        profesor_uuid = uuid.UUID(profesor_id)
        tipo_clase_uuid = uuid.UUID(tipo_clase_id)
    except ValueError as exc:
        raise UploadValidationError("Selecciona gimnasio, profesor y tipo de clase válidos.") from exc

    fecha_inicio = _parse_fecha(fecha)

    clase = Clase(
        gimnasio_id=gimnasio_uuid,
        profesor_id=profesor_uuid,
        tipo_clase_id=tipo_clase_uuid,
        nombre=nombre.strip(),
        fecha_inicio=fecha_inicio,
        sala=sala.strip() if sala else None,
        nivel=nivel.strip() if nivel else None,
        status="awaiting_upload",
    )
    db.session.add(clase)
    db.session.flush()

    bucket = current_app.config["S3_BUCKET"]
    uploads = {}

    for tipo, filename in (("video", video_filename), ("audio", audio_filename)):
        if not filename:
            continue
        ext = filename.rsplit(".", 1)[1].lower()
        key = f"clases/{clase.id}/{tipo}.{ext}"
        archivo = ArchivoMedia(
            tipo=tipo,
            nombre_original=filename,
            extension=ext,
            ruta_local=None,
            mime_type=None,
            tamano_bytes=None,
            s3_bucket=bucket,
            s3_key=key,
        )
        clase.archivos.append(archivo)
        uploads[tipo] = {
            "presigned_url": s3_client.generate_presigned_upload_url(bucket, key),
            "s3_bucket": bucket,
            "s3_key": key,
        }

    db.session.flush()

    for metrica in create_pending_metrics(clase):
        db.session.add(metrica)

    for job in create_pending_analysis_jobs(clase):
        db.session.add(job)

    db.session.commit()

    return {
        "clase_id": str(clase.id),
        "uploads": uploads,
        "redirect_url": url_for("dashboard.session_detail", clase_id=clase.id),
    }


def finalize_class_upload(clase_id: str) -> Clase:
    clase = get_clase(clase_id)
    if clase is None:
        raise UploadValidationError("Clase no encontrada.")

    if clase.status != "awaiting_upload":
        raise UploadValidationError("Clase ya finalizada.")

    for archivo in clase.archivos:
        if archivo.s3_key:
            if not s3_client.check_object_exists(archivo.s3_bucket, archivo.s3_key):
                raise UploadValidationError(f"Archivo {archivo.tipo} no encontrado en S3.")

    clase.status = "pendiente_analisis"
    db.session.commit()

    enqueue_analysis(str(clase.id))
    return clase
