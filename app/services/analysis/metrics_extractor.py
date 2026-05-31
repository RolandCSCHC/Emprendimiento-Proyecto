"""
Traduce respuestas crudas de AWS a las 5 métricas del dashboard.

Cada extractor recibe el dict ``combined_raw_data`` (llaveado por ``servicio``,
ver design) y devuelve ``{valor_numerico, unidad, confianza, detalle}``.
``apply_metrics_to_clase`` ejecuta todos los extractores y persiste en ``metricas``.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from app.services.analysis.constants import (
    SERVICE_FACE_DETECTION,
    SERVICE_PERSON_TRACKING,
    SERVICE_TRANSCRIBE,
)

UMBRAL_PERMANENCIA_PCT = 80


# --------------------------------------------------------------------------- #
# Helpers compartidos
# --------------------------------------------------------------------------- #
def _avg(values: list[float]) -> Optional[float]:
    return round(sum(values) / len(values), 4) if values else None


def _person_detections(combined: dict[str, Any]) -> list[dict[str, Any]]:
    pt = combined.get(SERVICE_PERSON_TRACKING) or {}
    return pt.get("persons") or []


def _video_duration_ms(combined: dict[str, Any]) -> Optional[int]:
    pt = combined.get(SERVICE_PERSON_TRACKING) or {}
    raw = pt.get("raw") or {}
    return (raw.get("VideoMetadata") or {}).get("DurationMillis")


def _index_timeline(persons: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    """Por PersonIndex: primera/última aparición (ms) y confianzas (0-1)."""
    timeline: dict[int, dict[str, Any]] = {}
    for det in persons:
        person = det.get("Person", {})
        idx = person.get("Index")
        if idx is None:
            continue
        ts = det.get("Timestamp", 0)
        entry = timeline.setdefault(idx, {"first": ts, "last": ts, "confianzas": []})
        entry["first"] = min(entry["first"], ts)
        entry["last"] = max(entry["last"], ts)
        conf = (person.get("Face") or {}).get("Confidence")
        if conf is not None:
            entry["confianzas"].append(conf / 100.0)
    return timeline


# --------------------------------------------------------------------------- #
# Métricas
# --------------------------------------------------------------------------- #
def extract_asistencia(raw_data: dict[str, Any]) -> dict[str, Any]:
    """Número de personas únicas detectadas (Rekognition PersonTracking)."""
    timeline = _index_timeline(_person_detections(raw_data))

    personas: list[dict[str, Any]] = []
    confs: list[float] = []
    for idx, e in sorted(timeline.items()):
        conf = _avg(e["confianzas"])
        personas.append(
            {"person_index": idx, "primera_aparicion_ms": e["first"], "confianza": conf}
        )
        if conf is not None:
            confs.append(conf)

    return {
        "valor_numerico": len(timeline),
        "unidad": "personas",
        "confianza": _avg(confs),
        "detalle": {"personas_detectadas": personas},
    }


def extract_permanencia(raw_data: dict[str, Any]) -> dict[str, Any]:
    """% de personas presentes ≥80% de la duración del video."""
    persons = _person_detections(raw_data)
    timeline = _index_timeline(persons)
    duracion = _video_duration_ms(raw_data) or max(
        (e["last"] for e in timeline.values()), default=0
    )

    if not timeline or not duracion:
        return {
            "valor_numerico": 0,
            "unidad": "porcentaje",
            "confianza": None,
            "detalle": {"timeline": [], "umbral_permanencia_pct": UMBRAL_PERMANENCIA_PCT},
        }

    detalle_timeline: list[dict[str, Any]] = []
    confs: list[float] = []
    permanecieron = 0
    for idx, e in sorted(timeline.items()):
        presencia_pct = min(100.0, round((e["last"] - e["first"]) / duracion * 100, 1))
        quedo = presencia_pct >= UMBRAL_PERMANENCIA_PCT
        if quedo:
            permanecieron += 1
        detalle_timeline.append(
            {
                "person_index": idx,
                "presencia_pct": presencia_pct,
                "salida_ms": None if quedo else e["last"],
            }
        )
        conf = _avg(e["confianzas"])
        if conf is not None:
            confs.append(conf)

    return {
        "valor_numerico": round(permanecieron / len(timeline) * 100, 1),
        "unidad": "porcentaje",
        "confianza": _avg(confs),
        "detalle": {
            "timeline": detalle_timeline,
            "umbral_permanencia_pct": UMBRAL_PERMANENCIA_PCT,
        },
    }


def extract_claridad_instrucciones(raw_data: dict[str, Any]) -> dict[str, Any]:
    """Score de claridad basado en WPM, longitud de frases y pausas (Transcribe)."""
    raise NotImplementedError


def extract_tiempo_hablando_vs_demostrando(raw_data: dict[str, Any]) -> dict[str, Any]:
    """Ratio tiempo con voz / tiempo total (Transcribe)."""
    raise NotImplementedError


def extract_satisfaccion_alumno(raw_data: dict[str, Any]) -> dict[str, Any]:
    """Score compuesto: emociones faciales + sentimiento del texto."""
    raise NotImplementedError


METRIC_EXTRACTORS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "asistencia": extract_asistencia,
    "permanencia": extract_permanencia,
    "claridad_instrucciones": extract_claridad_instrucciones,
    "tiempo_hablando_vs_demostrando": extract_tiempo_hablando_vs_demostrando,
    "satisfaccion_alumno": extract_satisfaccion_alumno,
}


def apply_metrics_to_clase(clase_id: str, combined_raw_data: dict[str, Any]) -> None:
    """Ejecuta todos los extractores y persiste en la tabla ``metricas``."""
    raise NotImplementedError("apply_metrics_to_clase pendiente (Task 14).")
