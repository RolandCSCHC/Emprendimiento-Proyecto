from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from flask import current_app

from app.models.session import ClassSession, MetricInfo


def _sessions_file() -> Path:
    return current_app.config["SESSIONS_FILE"]


def _ensure_store() -> None:
    path = _sessions_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(json.dumps({"sessions": []}, indent=2), encoding="utf-8")


def _read_all() -> list[ClassSession]:
    _ensure_store()
    data = json.loads(_sessions_file().read_text(encoding="utf-8"))
    return [ClassSession.from_dict(item) for item in data.get("sessions", [])]


def _write_all(sessions: list[ClassSession]) -> None:
    _ensure_store()
    payload = {"sessions": [session.to_dict() for session in sessions]}
    _sessions_file().write_text(json.dumps(payload, indent=2), encoding="utf-8")


def create_pending_metrics() -> dict[str, MetricInfo]:
    return {
        key: MetricInfo(status="pending")
        for key in current_app.config["METRIC_KEYS"]
    }


def create_session(
    nombre: str,
    fecha: str,
    video_filename: str | None = None,
    audio_filename: str | None = None,
) -> ClassSession:
    session = ClassSession(
        id=str(uuid4()),
        nombre=nombre,
        fecha=fecha,
        status="pending",
        video_filename=video_filename,
        audio_filename=audio_filename,
        metricas=create_pending_metrics(),
    )
    sessions = _read_all()
    sessions.insert(0, session)
    _write_all(sessions)
    return session


def list_sessions() -> list[ClassSession]:
    return _read_all()


def get_session(session_id: str) -> ClassSession | None:
    for session in _read_all():
        if session.id == session_id:
            return session
    return None


def update_session(session: ClassSession) -> ClassSession:
    sessions = _read_all()
    for index, item in enumerate(sessions):
        if item.id == session.id:
            sessions[index] = session
            _write_all(sessions)
            return session
    raise ValueError(f"Clase no encontrada: {session.id}")
