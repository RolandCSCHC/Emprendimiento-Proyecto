"""
Pipeline principal: valida S3 y lanza jobs AWS (Rekognition/Transcribe) por clase.

Invocado desde ``analysis_service.enqueue_analysis`` tras crear o editar una clase.
No bloquea: lanza jobs asíncronos y retorna; la completitud la maneja el job_poller
o el webhook SNS.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import quote

from flask import current_app

from app.extensions import db
from app.models import AnalisisJob, ArchivoMedia, Clase
from app.services.analysis.constants import (
    CLASE_ANALIZANDO,
    JOB_FAILED,
    JOB_SUBMITTED,
    SERVICE_FACE_DETECTION,
    SERVICE_PERSON_TRACKING,
    SERVICE_TRANSCRIBE,
    SERVICE_VALIDACION,
)
from app.services.aws import rekognition_client, s3_client, transcribe_client
from app.services.class_service import get_clase


def start_analysis_for_clase(clase_id: str) -> None:
    """Orquesta el lanzamiento de jobs AWS para una clase (ver requisitos 5.x)."""
    config = current_app.config
    if not config.get("AWS_ENABLED"):
        return

    clase = get_clase(clase_id)
    if clase is None:
        current_app.logger.warning(
            "start_analysis_for_clase: clase %s no existe", clase_id
        )
        return

    clase.status = CLASE_ANALIZANDO

    language_code = config.get("TRANSCRIBE_LANGUAGE_CODE", "es-ES")
    sns_topic_arn = config.get("SNS_TOPIC_ARN")
    output_bucket = config.get("TRANSCRIBE_OUTPUT_BUCKET")

    for archivo in clase.archivos:
        if not archivo.activo:
            continue
        _process_archivo(clase, archivo, language_code, sns_topic_arn, output_bucket)

    db.session.commit()


def _process_archivo(
    clase: Clase,
    archivo: ArchivoMedia,
    language_code: str,
    sns_topic_arn: Optional[str],
    output_bucket: Optional[str],
) -> None:
    if not archivo.s3_bucket or not archivo.s3_key:
        _record_failed_job(clase, archivo, "Archivo sin referencia S3 (bucket/key).")
        return

    try:
        exists = s3_client.check_object_exists(archivo.s3_bucket, archivo.s3_key)
    except Exception as exc:  # noqa: BLE001 - cualquier error de S3 marca el job
        _record_failed_job(clase, archivo, f"Error verificando S3: {exc}")
        return

    if not exists:
        _record_failed_job(
            clase,
            archivo,
            f"Objeto no encontrado en S3: s3://{archivo.s3_bucket}/{archivo.s3_key}",
        )
        return

    base = {"s3_bucket": archivo.s3_bucket, "s3_key": archivo.s3_key}

    if archivo.tipo == "video":
        pt_job = rekognition_client.start_person_tracking(
            archivo.s3_bucket, archivo.s3_key, sns_topic_arn
        )
        _record_submitted_job(
            clase, archivo, SERVICE_PERSON_TRACKING, pt_job,
            {**base, "service": SERVICE_PERSON_TRACKING, "sns_topic_arn": sns_topic_arn},
        )
        fd_job = rekognition_client.start_face_detection(
            archivo.s3_bucket, archivo.s3_key, sns_topic_arn
        )
        _record_submitted_job(
            clase, archivo, SERVICE_FACE_DETECTION, fd_job,
            {**base, "service": SERVICE_FACE_DETECTION, "sns_topic_arn": sns_topic_arn},
        )

    if archivo.tipo in ("video", "audio"):
        # URL-encode de la key (los nombres traen espacios y '#') para el MediaFileUri.
        s3_uri = f"s3://{archivo.s3_bucket}/{quote(archivo.s3_key)}"
        tr_job = transcribe_client.start_transcription(
            s3_uri, language_code, output_bucket
        )
        _record_submitted_job(
            clase, archivo, SERVICE_TRANSCRIBE, tr_job,
            {**base, "service": SERVICE_TRANSCRIBE, "language_code": language_code},
        )


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _record_submitted_job(
    clase: Clase,
    archivo: ArchivoMedia,
    servicio: str,
    job_id_externo: str,
    request_payload: dict[str, Any],
) -> None:
    db.session.add(
        AnalisisJob(
            clase_id=clase.id,
            archivo_media_id=archivo.id,
            proveedor="aws",
            servicio=servicio,
            job_id_externo=job_id_externo,
            status=JOB_SUBMITTED,
            request_payload=request_payload,
            started_at=_now(),
        )
    )


def _record_failed_job(clase: Clase, archivo: ArchivoMedia, error_mensaje: str) -> None:
    current_app.logger.warning(
        "Análisis fallido para archivo %s: %s", archivo.id, error_mensaje
    )
    db.session.add(
        AnalisisJob(
            clase_id=clase.id,
            archivo_media_id=archivo.id,
            proveedor="aws",
            servicio=SERVICE_VALIDACION,
            status=JOB_FAILED,
            error_mensaje=error_mensaje,
        )
    )
