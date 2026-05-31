"""Amazon Rekognition Video — detección de personas y de rostros/emociones.

Se usan dos APIs asíncronas separadas:
- ``StartPersonTracking`` / ``GetPersonTracking``: tracking temporal de personas
  (alimenta asistencia y permanencia).
- ``StartFaceDetection`` / ``GetFaceDetection`` con ``FaceAttributes='ALL'``:
  emociones por rostro (alimenta satisfacción del alumno).
"""

from __future__ import annotations

from typing import Any, Optional

from flask import current_app

from app.services.aws.boto_session import get_boto_client


def _notification_channel(sns_topic_arn: Optional[str]) -> Optional[dict[str, str]]:
    """
    Construye el ``NotificationChannel`` para SNS, si corresponde.

    Rekognition exige un ``RoleArn`` (rol que asume para publicar en SNS) junto
    al topic. Si falta el topic o el rol (config ``REKOGNITION_SNS_ROLE_ARN``),
    se omite la notificación y el resultado se obtiene por polling.
    """
    if not sns_topic_arn:
        return None
    role_arn = current_app.config.get("REKOGNITION_SNS_ROLE_ARN")
    if not role_arn:
        return None
    return {"SNSTopicArn": sns_topic_arn, "RoleArn": role_arn}


def start_person_tracking(
    bucket: str, key: str, sns_topic_arn: Optional[str] = None
) -> str:
    """Inicia ``StartPersonTracking``. Retorna el ``JobId`` de AWS."""
    client = get_boto_client("rekognition")
    params: dict[str, Any] = {"Video": {"S3Object": {"Bucket": bucket, "Name": key}}}
    channel = _notification_channel(sns_topic_arn)
    if channel:
        params["NotificationChannel"] = channel
    response = client.start_person_tracking(**params)
    return response["JobId"]


def start_face_detection(
    bucket: str, key: str, sns_topic_arn: Optional[str] = None
) -> str:
    """Inicia ``StartFaceDetection`` con ``FaceAttributes='ALL'`` (incluye emociones)."""
    client = get_boto_client("rekognition")
    params: dict[str, Any] = {
        "Video": {"S3Object": {"Bucket": bucket, "Name": key}},
        "FaceAttributes": "ALL",
    }
    channel = _notification_channel(sns_topic_arn)
    if channel:
        params["NotificationChannel"] = channel
    response = client.start_face_detection(**params)
    return response["JobId"]


def _iter_pages(getter, job_id: str):
    """Itera las páginas de un getter de Rekognition siguiendo ``NextToken``."""
    page = getter(JobId=job_id)
    yield page
    token = page.get("NextToken")
    while token:
        page = getter(JobId=job_id, NextToken=token)
        yield page
        token = page.get("NextToken")


def get_person_tracking_result(job_id: str) -> dict[str, Any]:
    """
    Consulta ``GetPersonTracking`` y **agrega al vuelo** (no guarda cada frame).

    Returns:
        ``{status, persons, video_duration_ms}`` donde ``persons`` es un dict
        ``{indice: {first_ms, last_ms, conf}}``. Compacto e independiente de la
        duración del video (evita el límite de 256 MB de JSONB en Postgres).
    """
    client = get_boto_client("rekognition")
    status: Optional[str] = None
    duration = None
    acc: dict[int, dict[str, Any]] = {}
    for page in _iter_pages(client.get_person_tracking, job_id):
        if status is None:
            status = page.get("JobStatus")
            if status == "FAILED":
                return {"status": "FAILED", "error": page.get("StatusMessage")}
            duration = (page.get("VideoMetadata") or {}).get("DurationMillis")
        for det in page.get("Persons", []):
            person = det.get("Person", {})
            idx = person.get("Index")
            if idx is None:
                continue
            ts = det.get("Timestamp", 0)
            entry = acc.setdefault(idx, {"first_ms": ts, "last_ms": ts, "conf_sum": 0.0, "conf_n": 0})
            entry["first_ms"] = min(entry["first_ms"], ts)
            entry["last_ms"] = max(entry["last_ms"], ts)
            conf = (person.get("Face") or {}).get("Confidence")
            if conf is not None:
                entry["conf_sum"] += conf / 100.0
                entry["conf_n"] += 1

    persons = {
        str(idx): {
            "first_ms": e["first_ms"],
            "last_ms": e["last_ms"],
            "conf": round(e["conf_sum"] / e["conf_n"], 4) if e["conf_n"] else None,
        }
        for idx, e in acc.items()
    }
    return {"status": status, "persons": persons, "video_duration_ms": duration}


def get_face_detection_result(job_id: str) -> dict[str, Any]:
    """
    Consulta ``GetFaceDetection`` y **agrega emociones al vuelo** (no guarda cada rostro).

    Returns:
        ``{status, emotions, face_count, avg_confidence}`` donde ``emotions`` es la
        suma de confianza por tipo de emoción. Compacto (unos KB) sin importar la
        duración del video.
    """
    client = get_boto_client("rekognition")
    status: Optional[str] = None
    emotions: dict[str, float] = {}
    conf_sum = 0.0
    face_count = 0
    for page in _iter_pages(client.get_face_detection, job_id):
        if status is None:
            status = page.get("JobStatus")
            if status == "FAILED":
                return {"status": "FAILED", "error": page.get("StatusMessage")}
        for f in page.get("Faces", []):
            face = f.get("Face") or {}
            conf = face.get("Confidence")
            if conf is not None:
                conf_sum += conf / 100.0
            face_count += 1
            for emo in face.get("Emotions") or []:
                tipo, ec = emo.get("Type"), emo.get("Confidence")
                if tipo is None or ec is None:
                    continue
                emotions[tipo] = emotions.get(tipo, 0.0) + ec

    return {
        "status": status,
        "emotions": emotions,
        "face_count": face_count,
        "avg_confidence": round(conf_sum / face_count, 4) if face_count else None,
    }
