"""Amazon Transcribe — transcripción de audio para claridad y ratio habla/demo.

El resultado incluye timestamps a nivel de palabra (items), que alimentan las
métricas de claridad de instrucciones y tiempo hablando vs. demostrando.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

import requests

from app.services.aws.boto_session import get_boto_client


def start_transcription(
    s3_uri: str,
    language_code: Optional[str] = None,
    output_bucket: Optional[str] = None,
    language_options: Optional[list[str]] = None,
) -> str:
    """
    Inicia un job de transcripción con timestamps por palabra.

    - Si ``language_code`` es un código concreto (es-ES, en-US, ...), lo usa.
    - Si es ``None`` o ``"auto"``, activa la **detección automática de idioma**
      (``IdentifyLanguage``) entre ``language_options`` (por defecto es-ES/en-US).

    Args:
        s3_uri: URI del audio/video en S3 (``s3://bucket/key``).
        language_code: código de idioma, o ``None``/``"auto"`` para auto-detectar.
        output_bucket: bucket de salida opcional.
        language_options: idiomas candidatos para la auto-detección.

    Returns:
        El nombre del job de transcripción.
    """
    client = get_boto_client("transcribe")
    job_name = f"gymsight-{uuid.uuid4()}"

    params: dict[str, Any] = {
        "TranscriptionJobName": job_name,
        "Media": {"MediaFileUri": s3_uri},
    }

    if language_code and language_code != "auto":
        params["LanguageCode"] = language_code
    else:
        params["IdentifyLanguage"] = True
        params["LanguageOptions"] = list(language_options) if language_options else ["es-ES", "en-US"]

    media_format = s3_uri.rsplit(".", 1)[-1].lower() if "." in s3_uri else None
    if media_format in {"mp3", "mp4", "wav", "flac", "ogg", "amr", "webm"}:
        params["MediaFormat"] = media_format

    if output_bucket:
        params["OutputBucketName"] = output_bucket

    client.start_transcription_job(**params)
    return job_name


def _normalize_status(transcribe_status: Optional[str]) -> str:
    """Normaliza el estado de Transcribe al vocabulario común del poller."""
    if transcribe_status == "COMPLETED":
        return "SUCCEEDED"
    if transcribe_status == "FAILED":
        return "FAILED"
    return "IN_PROGRESS"  # QUEUED | IN_PROGRESS


def get_transcription_result(job_name: str) -> dict[str, Any]:
    """
    Consulta ``GetTranscriptionJob`` y, si terminó, descarga el JSON de resultados.

    Returns:
        Dict con ``status`` (IN_PROGRESS|SUCCEEDED|FAILED), ``transcript`` (texto
        completo o ``None``) y ``raw`` (JSON de resultados con items, o metadata
        del job si aún no terminó). Incluye ``error`` si el job falló.
    """
    client = get_boto_client("transcribe")
    response = client.get_transcription_job(TranscriptionJobName=job_name)
    job = response["TranscriptionJob"]
    status = _normalize_status(job.get("TranscriptionJobStatus"))

    if status == "FAILED":
        return {
            "status": "FAILED",
            "transcript": None,
            "raw": job,
            "error": job.get("FailureReason"),
        }

    if status != "SUCCEEDED":
        return {"status": status, "transcript": None, "raw": job}

    transcript_uri = job["Transcript"]["TranscriptFileUri"]
    data = requests.get(transcript_uri, timeout=30).json()
    transcript_text = data["results"]["transcripts"][0]["transcript"]
    return {
        "status": "SUCCEEDED",
        "transcript": transcript_text,
        "raw": data,
        # Idioma detectado por Transcribe (útil cuando se usó auto-detección).
        "language_code": job.get("LanguageCode"),
    }
