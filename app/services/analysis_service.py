"""
Punto de entrada del análisis AWS para Gymsight.

La app llama ``enqueue_analysis`` tras subir o reemplazar archivos de una clase.
El resto del flujo vive en ``app/services/analysis/`` y ``app/services/aws/``.
"""

from __future__ import annotations


def enqueue_analysis(clase_id: str) -> None:
    """
    Encola el análisis de una clase (no bloqueante).

    Hoy es un no-op para no romper la app. Cuando implementes AWS:
    1. Comprueba ``current_app.config['AWS_ENABLED']``.
    2. Descomenta la llamada a ``start_analysis_for_clase``.

    Args:
        clase_id: UUID de la clase en la tabla ``clases``.
    """
    from flask import current_app

    if not current_app.config.get("AWS_ENABLED"):
        return

    from app.services.analysis.pipeline import start_analysis_for_clase

    start_analysis_for_clase(clase_id)


def poll_pending_jobs() -> int:
    """
    Consulta jobs AWS pendientes. Usar desde CLI: ``flask aws-poll-jobs``.

    Returns:
        Cantidad de jobs procesados.
    """
    from app.services.analysis.job_poller import poll_pending_jobs as _poll

    return _poll()


def process_completed_job(analisis_job_id: str) -> None:
    """
    Procesa un job completado (desde poller o webhook SNS).

    Args:
        analisis_job_id: UUID en ``analisis_jobs``.
    """
    from app.services.analysis.job_poller import process_completed_job as _process

    _process(analisis_job_id)
