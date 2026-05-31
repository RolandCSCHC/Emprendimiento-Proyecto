"""
Consulta de jobs AWS pendientes y procesamiento de resultados.

Ejecutar con: ``flask aws-poll-jobs`` (cron cada 1-5 min en producción).
El webhook SNS usa ``process_completed_job`` para baja latencia.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.extensions import db
from app.models import AnalisisJob
from app.services.analysis.constants import (
    CLASE_ERROR,
    JOB_COMPLETED,
    JOB_FAILED,
    JOB_IN_PROGRESS,
    JOB_SUBMITTED,
    SERVICE_FACE_DETECTION,
    SERVICE_PERSON_TRACKING,
    SERVICE_TRANSCRIBE,
)
from app.services.analysis.metrics_extractor import apply_metrics_to_clase
from app.services.aws import rekognition_client, transcribe_client

# Mapeo servicio -> función que consulta el resultado en AWS.
_GETTERS = {
    SERVICE_PERSON_TRACKING: rekognition_client.get_person_tracking_result,
    SERVICE_FACE_DETECTION: rekognition_client.get_face_detection_result,
    SERVICE_TRANSCRIBE: transcribe_client.get_transcription_result,
}


def poll_pending_jobs() -> int:
    """
    Consulta los jobs en ``submitted``/``in_progress``, actualiza su estado y,
    cuando todos los jobs de una clase están completos, dispara las métricas.

    Returns:
        Cantidad de jobs procesados en esta ejecución.
    """
    jobs = AnalisisJob.query.filter(
        AnalisisJob.status.in_([JOB_SUBMITTED, JOB_IN_PROGRESS])
    ).all()

    clases_afectadas: set[uuid.UUID] = set()
    for job in jobs:
        _refresh_job(job)
        clases_afectadas.add(job.clase_id)

    db.session.commit()

    for clase_id in clases_afectadas:
        _maybe_extract_metrics(clase_id)

    return len(jobs)


def process_completed_job(analisis_job_id: str) -> None:
    """Procesa un único job (usado desde el webhook SNS)."""
    job = db.session.get(AnalisisJob, _as_uuid(analisis_job_id))
    if job is None:
        return
    _refresh_job(job)
    db.session.commit()
    _maybe_extract_metrics(job.clase_id)


def _refresh_job(job: AnalisisJob) -> None:
    """Consulta AWS y actualiza el estado del job según el resultado."""
    result = _query_service(job.servicio, job.job_id_externo)
    if result is None:
        return

    status = result.get("status")
    if status == "SUCCEEDED":
        job.raw_response = result
        job.status = JOB_COMPLETED
        job.completed_at = _now()
    elif status == "FAILED":
        job.status = JOB_FAILED
        job.error_mensaje = result.get("error")
        job.completed_at = _now()
        job.clase.status = CLASE_ERROR
    else:
        job.status = JOB_IN_PROGRESS


def _query_service(servicio: str, job_id_externo: Optional[str]) -> Optional[dict[str, Any]]:
    getter = _GETTERS.get(servicio)
    if getter is None or not job_id_externo:
        return None
    return getter(job_id_externo)


def _maybe_extract_metrics(clase_id: uuid.UUID) -> None:
    """
    Calcula las métricas cuando todos los jobs de la clase llegan a un estado
    terminal (completado o fallido) y al menos uno se completó. Las métricas
    cuyos datos no estén disponibles (job fallido) se calculan con lo que haya.
    """
    jobs = AnalisisJob.query.filter_by(clase_id=clase_id).all()
    if not jobs:
        return
    terminal = {JOB_COMPLETED, JOB_FAILED}
    if all(job.status in terminal for job in jobs) and any(
        job.status == JOB_COMPLETED for job in jobs
    ):
        combined = _build_combined_raw_data(jobs)
        apply_metrics_to_clase(str(clase_id), combined)


def _build_combined_raw_data(jobs: list[AnalisisJob]) -> dict[str, Any]:
    """Arma el dict llaveado por ``servicio`` para el metrics_extractor."""
    return {job.servicio: job.raw_response for job in jobs if job.raw_response}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_uuid(value: str | uuid.UUID) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
