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


def _collect_paginated(getter, job_id: str, items_key: str) -> dict[str, Any]:
    """
    Llama al getter de Rekognition paginando con ``NextToken`` y acumula
    ``items_key`` (``Persons`` o ``Faces``).

    Returns:
        Dict con ``status`` (IN_PROGRESS|SUCCEEDED|FAILED), ``raw`` (respuesta con
        todos los items acumulados) y la lista bajo la clave en minúscula.
        Incluye ``error`` con el mensaje de AWS si el job falló.
    """
    response = getter(JobId=job_id)
    status = response.get("JobStatus")
    items = list(response.get(items_key, []))
    next_token = response.get("NextToken")
    while next_token:
        page = getter(JobId=job_id, NextToken=next_token)
        items.extend(page.get(items_key, []))
        next_token = page.get("NextToken")

    raw = dict(response)
    raw[items_key] = items
    raw.pop("NextToken", None)

    result: dict[str, Any] = {"status": status, "raw": raw, items_key.lower(): items}
    if status == "FAILED":
        result["error"] = response.get("StatusMessage")
    return result


def get_person_tracking_result(job_id: str) -> dict[str, Any]:
    """Consulta ``GetPersonTracking``. Retorna ``{status, raw, persons}``."""
    client = get_boto_client("rekognition")
    return _collect_paginated(client.get_person_tracking, job_id, "Persons")


def get_face_detection_result(job_id: str) -> dict[str, Any]:
    """Consulta ``GetFaceDetection``. Retorna ``{status, raw, faces}``."""
    client = get_boto_client("rekognition")
    return _collect_paginated(client.get_face_detection, job_id, "Faces")
