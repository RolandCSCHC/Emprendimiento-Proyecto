from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from flask import current_app

from app.extensions import db
from app.models import AnalisisJob, ArchivoMedia, Clase
from app.services.analysis_service import enqueue_analysis
from app.services.class_service import (
    create_pending_analysis_jobs,
    create_pending_metrics,
    get_clase,
)


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


def create_class_session(
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
    if not nombre.strip():
        raise UploadValidationError("El nombre de la clase es obligatorio.")

    has_video = video and video.filename
    has_audio = audio and audio.filename

    if not has_video and not has_audio:
        raise UploadValidationError("Debes subir al menos un archivo de video o audio.")

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

    clase = Clase(
        gimnasio_id=gimnasio_uuid,
        profesor_id=profesor_uuid,
        tipo_clase_id=tipo_clase_uuid,
        nombre=nombre.strip(),
        fecha_inicio=fecha_inicio,
        sala=sala.strip() if sala else None,
        nivel=nivel.strip() if nivel else None,
        status="pendiente_analisis",
    )
    db.session.add(clase)
    db.session.flush()

    if has_video:
        clase.archivos.append(_save_file(clase.id, video, "video"))
    if has_audio:
        clase.archivos.append(_save_file(clase.id, audio, "audio"))

    db.session.flush()

    for metrica in create_pending_metrics(clase):
        db.session.add(metrica)

    for job in create_pending_analysis_jobs(clase):
        db.session.add(job)

    db.session.commit()
    enqueue_analysis(str(clase.id))
    return clase


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
