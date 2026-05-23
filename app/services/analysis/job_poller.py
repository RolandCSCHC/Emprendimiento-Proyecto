"""
Consulta periódica de jobs AWS pendientes.

Ejecutar con: ``docker compose exec web flask aws-poll-jobs``
(o un contenedor worker dedicado en producción).
"""

from __future__ import annotations


def poll_pending_jobs() -> int:
    """
    Busca ``analisis_jobs`` con status ``submitted`` o ``in_progress`` y actualiza.

    Por cada job:
    1. Según ``servicio``, llamar ``get_video_job_result`` o ``get_transcription_result``.
    2. Si sigue en progreso: actualizar status y continuar.
    3. Si terminó con éxito:
       - Guardar ``raw_response`` en el job.
       - Llamar ``metrics_extractor.apply_metrics_to_clase`` con los datos acumulados.
    4. Si falló: ``status='failed'``, ``error_mensaje``, ``clase.status='error'``.

    Returns:
        Número de jobs procesados en esta ejecución.
    """
    raise NotImplementedError("Job poller AWS pendiente. Ver README — Fase AWS.")


def process_completed_job(analisis_job_id: str) -> None:
    """
    Procesa un único job ya completado (útil desde webhooks SNS).

    Args:
        analisis_job_id: UUID del registro en ``analisis_jobs``.
    """
    raise NotImplementedError("Procesamiento de jobs AWS pendiente. Ver README — Fase AWS.")
