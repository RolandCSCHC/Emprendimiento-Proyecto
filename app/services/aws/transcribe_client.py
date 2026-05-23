"""Amazon Transcribe — transcripción de audio para claridad de instrucciones."""

from __future__ import annotations

from typing import Any


def start_transcription(s3_uri: str, language_code: str = "es-ES") -> str:
    """
    Inicia la transcripción de un archivo de audio (o pista de audio de video).

    Args:
        s3_uri: URI del audio en S3.
        language_code: Código de idioma (es-ES, es-US, etc.).

    Returns:
        ``job_id`` o nombre del job de Transcribe.
    """
    raise NotImplementedError("Integración Transcribe pendiente. Ver README — Fase AWS.")


def get_transcription_result(job_name: str) -> dict[str, Any]:
    """
    Obtiene el resultado de la transcripción.

    Returns:
        Dict con ``status``, ``transcript`` (texto) y ``raw`` (respuesta completa).
        El texto alimenta métricas como claridad_instrucciones y hablando vs. demostrando.
    """
    raise NotImplementedError("Integración Transcribe pendiente. Ver README — Fase AWS.")
