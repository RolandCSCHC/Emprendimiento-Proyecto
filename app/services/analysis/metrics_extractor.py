"""
Traduce respuestas crudas de AWS a las 5 métricas del dashboard.

Cada métrica se persiste en la tabla ``metricas`` (valor_numerico, detalle JSONB, status).
"""

from __future__ import annotations

from typing import Any, Callable


def extract_asistencia(raw_data: dict[str, Any]) -> dict[str, Any]:
    """
    Métrica: asistencia (número de participantes detectados).

    Fuente típica: Rekognition person detection / label detection.
    """
    raise NotImplementedError


def extract_permanencia(raw_data: dict[str, Any]) -> dict[str, Any]:
    """
    Métrica: permanencia (% o tiempo medio que permanecen en la sesión).

    Fuente típica: tracking de personas en el tiempo (Rekognition).
    """
    raise NotImplementedError


def extract_claridad_instrucciones(raw_data: dict[str, Any]) -> dict[str, Any]:
    """
    Métrica: claridad de instrucciones (score o texto resumen).

    Fuente típica: Transcribe (palabras/min, pausas, longitud de frases).
    """
    raise NotImplementedError


def extract_tiempo_hablando_vs_demostrando(raw_data: dict[str, Any]) -> dict[str, Any]:
    """
    Métrica: tiempo hablando vs. demostrando (ratio o segundos por categoría).

    Fuente típica: Transcribe (segmentos con voz) + Rekognition (movimiento/actividad).
    """
    raise NotImplementedError


def extract_satisfaccion_alumno(raw_data: dict[str, Any]) -> dict[str, Any]:
    """
    Métrica: satisfacción del alumno (score inferido).

    Fuente típica: Rekognition face/emotion o Comprehend sobre transcript.
    """
    raise NotImplementedError


METRIC_EXTRACTORS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "asistencia": extract_asistencia,
    "permanencia": extract_permanencia,
    "claridad_instrucciones": extract_claridad_instrucciones,
    "tiempo_hablando_vs_demostrando": extract_tiempo_hablando_vs_demostrando,
    "satisfaccion_alumno": extract_satisfaccion_alumno,
}


def apply_metrics_to_clase(clase_id: str, combined_raw_data: dict[str, Any]) -> None:
    """
    Aplica todos los extractores y actualiza la base de datos.

    Cada extractor debe devolver algo como::

        {
            "valor_numerico": 18,
            "valor_texto": None,
            "unidad": "personas",
            "confianza": 0.92,
            "detalle": { ... }
        }

    Luego:
    - UPDATE metricas SET status='completed', ...
    - Si todas las métricas están listas: clase.status = 'completada'
    """
    raise NotImplementedError("Extractor de métricas AWS pendiente. Ver README — Fase AWS.")
