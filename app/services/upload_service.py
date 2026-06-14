from __future__ import annotations

import os
import uuid
from datetime import datetime
from pathlib import Path

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from flask import current_app, url_for

from app.extensions import db
from app.models import ArchivoMedia, Clase, ProgramaClase
from app.services.analysis.constants import CLASE_AWAITING_UPLOAD
from app.services.analysis_service import enqueue_analysis
from app.services.aws import s3_client
from app.services.class_service import create_pending_metrics, get_clase
from app.services.programa_service import get_programa


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


def _stream_size(file: FileStorage) -> int:
    """Tamaño del archivo subido, sin consumir el stream."""
    stream = file.stream
    pos = stream.tell()
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    stream.seek(pos)
    return size


def _save_file(clase_id: uuid.UUID, file: FileStorage, prefix: str) -> ArchivoMedia:
    original = secure_filename(file.filename or "")
    extension = original.rsplit(".", 1)[1].lower()
    tipo = "video" if prefix == "video" else "audio"

    # Con AWS activo: el archivo va directo a S3 (no al disco). El pipeline lo
    # procesará desde ahí. Sin AWS: se guarda local para que la app funcione igual.
    if current_app.config.get("AWS_ENABLED"):
        bucket = current_app.config["S3_BUCKET"]
        key = f"clases/{clase_id}/{prefix}.{extension}"
        tamano = _stream_size(file)
        s3_client.upload_fileobj(file.stream, bucket, key, content_type=file.mimetype)
        return ArchivoMedia(
            tipo=tipo,
            nombre_original=original,
            extension=extension,
            s3_bucket=bucket,
            s3_key=key,
            tamano_bytes=tamano,
            mime_type=file.mimetype,
        )

    filename = f"{prefix}.{extension}"
    clase_dir = current_app.config["UPLOAD_FOLDER"] / str(clase_id)
    clase_dir.mkdir(parents=True, exist_ok=True)
    destination = clase_dir / filename
    file.save(destination)
    tamano = destination.stat().st_size
    return ArchivoMedia(
        tipo=tipo,
        nombre_original=original,
        extension=extension,
        ruta_local=str(Path(str(clase_id)) / filename),
        tamano_bytes=tamano,
        mime_type=file.mimetype,
    )


def _session_nombre(programa: ProgramaClase, fecha_inicio: datetime) -> str:
    return f"{programa.nombre} — {fecha_inicio.strftime('%d/%m/%Y %H:%M')}"


def create_pending_session(
    *,
    programa_id: str,
    fecha: str,
    video_filename: str | None = None,
    audio_filename: str | None = None,
) -> dict:
    """
    Crea una sesión en estado ``awaiting_upload`` y devuelve URLs pre-firmadas para
    que el navegador suba los archivos **directo a S3** (sin pasar por el servidor).
    Hereda metadata del programa padre.
    """
    if not video_filename and not audio_filename:
        raise UploadValidationError("Debes subir al menos un archivo de video o audio.")

    if video_filename and not _allowed_file(
        video_filename, current_app.config["ALLOWED_VIDEO_EXTENSIONS"]
    ):
        raise UploadValidationError("Formato de video no permitido. Usa: mp4, webm o mov.")

    if audio_filename and not _allowed_file(
        audio_filename, current_app.config["ALLOWED_AUDIO_EXTENSIONS"]
    ):
        raise UploadValidationError("Formato de audio no permitido. Usa: mp3, wav, m4a u ogg.")

    programa = get_programa(programa_id)
    if programa is None:
        raise UploadValidationError("Clase no encontrada.")

    fecha_inicio = _parse_fecha(fecha)

    clase = Clase(
        gimnasio_id=programa.gimnasio_id,
        profesor_id=programa.profesor_id,
        tipo_clase_id=programa.tipo_clase_id,
        programa_id=programa.id,
        nombre=_session_nombre(programa, fecha_inicio),
        fecha_inicio=fecha_inicio,
        sala=programa.sala,
        nivel=programa.nivel,
        status=CLASE_AWAITING_UPLOAD,
    )
    db.session.add(clase)
    db.session.flush()

    bucket = current_app.config["S3_BUCKET"]
    uploads: dict[str, dict] = {}
    for tipo, filename in (("video", video_filename), ("audio", audio_filename)):
        if not filename:
            continue
        ext = filename.rsplit(".", 1)[1].lower()
        key = f"clases/{clase.id}/{tipo}.{ext}"
        clase.archivos.append(
            ArchivoMedia(
                tipo=tipo,
                nombre_original=secure_filename(filename),
                extension=ext,
                s3_bucket=bucket,
                s3_key=key,
            )
        )
        uploads[tipo] = {
            "presigned_url": s3_client.generate_presigned_upload_url(bucket, key),
            "s3_bucket": bucket,
            "s3_key": key,
        }

    db.session.flush()

    for metrica in create_pending_metrics(clase):
        db.session.add(metrica)

    db.session.commit()

    return {
        "clase_id": str(clase.id),
        "programa_id": str(programa.id),
        "uploads": uploads,
        "redirect_url": url_for("dashboard.session_detail", clase_id=clase.id),
    }


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
    """Compatibilidad: crea programa + sesión en un paso."""
    from app.services.programa_service import create_programa

    programa = create_programa(
        nombre=nombre,
        gimnasio_id=gimnasio_id,
        profesor_id=profesor_id,
        tipo_clase_id=tipo_clase_id,
        sala=sala,
        nivel=nivel,
    )
    return create_pending_session(
        programa_id=str(programa.id),
        fecha=fecha,
        video_filename=video_filename,
        audio_filename=audio_filename,
    )


def finalize_class_upload(clase_id: str) -> Clase:
    """Verifica que los archivos llegaron a S3, marca la clase lista y dispara el análisis."""
    clase = get_clase(clase_id)
    if clase is None:
        raise UploadValidationError("Clase no encontrada.")
    if clase.status != CLASE_AWAITING_UPLOAD:
        raise UploadValidationError("Clase ya finalizada.")

    for archivo in clase.archivos:
        if archivo.s3_key and not s3_client.check_object_exists(
            archivo.s3_bucket, archivo.s3_key
        ):
            raise UploadValidationError(f"Archivo {archivo.tipo} no encontrado en S3.")

    clase.status = "pendiente_analisis"
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

    db.session.commit()

    if has_video or has_audio:
        enqueue_analysis(str(clase.id))

    return clase
