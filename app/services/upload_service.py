from __future__ import annotations

from pathlib import Path
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from flask import current_app

from app.services.analysis_service import enqueue_analysis
from app.services.session_store import create_session, update_session


class UploadValidationError(Exception):
    pass


def _allowed_file(filename: str, allowed: set[str]) -> bool:
    if "." not in filename:
        return False
    extension = filename.rsplit(".", 1)[1].lower()
    return extension in allowed


def _save_file(session_id: str, file: FileStorage, prefix: str) -> str:
    original = secure_filename(file.filename or "")
    extension = original.rsplit(".", 1)[1].lower()
    filename = f"{prefix}.{extension}"
    session_dir = current_app.config["UPLOAD_FOLDER"] / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    destination = session_dir / filename
    file.save(destination)
    return str(Path(session_id) / filename)


def create_class_session(
    nombre: str,
    fecha: str,
    video: FileStorage | None,
    audio: FileStorage | None,
):
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

    session = create_session(nombre=nombre.strip(), fecha=fecha)

    video_path = None
    audio_path = None

    if has_video:
        video_path = _save_file(session.id, video, "video")
    if has_audio:
        audio_path = _save_file(session.id, audio, "audio")

    session.video_filename = video_path
    session.audio_filename = audio_path
    session = update_session(session)

    enqueue_analysis(session.id)
    return session
