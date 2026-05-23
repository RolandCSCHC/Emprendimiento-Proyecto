"""Amazon Rekognition Video — detección de personas, movimiento, engagement."""

from __future__ import annotations

from typing import Any


def start_video_analysis(s3_uri: str) -> str:
    """
    Inicia un job asíncrono de análisis de video.

    Servicios Rekognition útiles para Gymsight:
    - ``StartLabelDetection``: etiquetas y escenas.
    - ``StartPersonTracking`` / detección de personas: asistencia y permanencia.
    - ``StartFaceDetection``: aproximación de engagement / satisfacción.

    Args:
        s3_uri: URI del video en S3 (``s3://bucket/key``).

    Returns:
        ``job_id`` externo de AWS (guardar en ``analisis_jobs.job_id_externo``).
    """
    raise NotImplementedError("Integración Rekognition pendiente. Ver README — Fase AWS.")


def get_video_job_result(job_id: str) -> dict[str, Any]:
    """
    Consulta el estado y resultado de un job de Rekognition.

    Returns:
        Dict con ``status`` (IN_PROGRESS | SUCCEEDED | FAILED) y ``raw`` (respuesta API).
        Guardar ``raw`` en ``analisis_jobs.raw_response`` (JSONB).
    """
    raise NotImplementedError("Integración Rekognition pendiente. Ver README — Fase AWS.")
