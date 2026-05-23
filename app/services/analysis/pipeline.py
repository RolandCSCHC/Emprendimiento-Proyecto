"""
Pipeline principal: S3 → jobs AWS → actualización de analisis_jobs.

Invocado desde ``analysis_service.enqueue_analysis`` tras crear o editar una clase.
"""

from __future__ import annotations


def start_analysis_for_clase(clase_id: str) -> None:
    """
    Orquesta el análisis completo de una clase.

    Flujo a implementar:
    1. Cargar la clase con ``get_clase(clase_id)`` (archivos, jobs, métricas).
    2. Poner ``clase.status = 'analizando'``.
    3. Por cada ``archivo`` en ``clase.archivos``:
       a. Si no tiene ``s3_key``: subir con ``aws.s3_client.upload_archivo_to_s3``.
       b. Video → ``rekognition_client.start_video_analysis(s3_uri)``.
       c. Audio (o audio del video) → ``transcribe_client.start_transcription(s3_uri)``.
       d. Crear o actualizar fila en ``analisis_jobs``:
          - ``servicio``: rekognition | transcribe
          - ``job_id_externo``: ID devuelto por AWS
          - ``status``: submitted
          - ``started_at``: now
    4. ``db.session.commit()``.

  No bloquear la petición HTTP esperando resultados; los jobs son asíncronos.
  Usar ``job_poller`` o webhooks para completar.
    """
    raise NotImplementedError("Pipeline AWS pendiente. Ver README — Fase AWS.")
