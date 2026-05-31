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
WPM_OPTIMO = (120, 160)  # palabras/min óptimas para instrucciones de fitness
LONGITUD_FRASE_OPTIMA = (8, 15)  # palabras por frase
PAUSAS_POR_MIN_OPTIMO = (2, 8)
PAUSE_THRESHOLD_S = 1.5  # gap entre palabras que separa frases
SPEECH_GAP_S = 0.5  # gap máximo dentro de un mismo segmento de habla


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


def _transcribe_words(combined: dict[str, Any]) -> list[dict[str, Any]]:
    """Extrae las palabras (items 'pronunciation') con start/end/confianza."""
    tr = combined.get(SERVICE_TRANSCRIBE) or {}
    raw = tr.get("raw") or {}
    items = (raw.get("results") or {}).get("items") or []
    words: list[dict[str, Any]] = []
    for item in items:
        if item.get("type") != "pronunciation":
            continue
        try:
            start = float(item["start_time"])
            end = float(item["end_time"])
        except (KeyError, ValueError, TypeError):
            continue
        conf = None
        alts = item.get("alternatives") or []
        if alts:
            try:
                conf = float(alts[0].get("confidence"))
            except (TypeError, ValueError):
                conf = None
        words.append({"start": start, "end": end, "conf": conf})
    return words


def _rango_score(value: float, low: float, high: float, penalti: float = 1.0) -> float:
    """100 si value está en [low, high]; baja linealmente fuera del rango."""
    if low <= value <= high:
        return 100.0
    dist = (low - value) if value < low else (value - high)
    return max(0.0, 100.0 - penalti * dist)


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
    words = _transcribe_words(raw_data)
    detalle_vacio = {
        "palabras_por_minuto": 0,
        "longitud_promedio_frase": 0,
        "frecuencia_pausas_por_minuto": 0,
        "rango_optimo_wpm": list(WPM_OPTIMO),
    }
    if len(words) < 2:
        return {"valor_numerico": 0, "unidad": "score", "confianza": None, "detalle": detalle_vacio}

    total_words = len(words)
    dur_min = (words[-1]["end"] - words[0]["start"]) / 60
    wpm = total_words / dur_min if dur_min > 0 else 0

    pausas = sum(
        1 for prev, cur in zip(words, words[1:])
        if cur["start"] - prev["end"] >= PAUSE_THRESHOLD_S
    )
    frases = pausas + 1
    long_prom_frase = total_words / frases
    pausas_por_min = pausas / dur_min if dur_min > 0 else 0

    score = round(
        0.5 * _rango_score(wpm, *WPM_OPTIMO, penalti=1.0)
        + 0.25 * _rango_score(long_prom_frase, *LONGITUD_FRASE_OPTIMA, penalti=5.0)
        + 0.25 * _rango_score(pausas_por_min, *PAUSAS_POR_MIN_OPTIMO, penalti=5.0)
    )
    confs = [w["conf"] for w in words if w["conf"] is not None]
    return {
        "valor_numerico": score,
        "unidad": "score",
        "confianza": _avg(confs),
        "detalle": {
            "palabras_por_minuto": round(wpm, 1),
            "longitud_promedio_frase": round(long_prom_frase, 1),
            "frecuencia_pausas_por_minuto": round(pausas_por_min, 1),
            "rango_optimo_wpm": list(WPM_OPTIMO),
        },
    }


def extract_tiempo_hablando_vs_demostrando(raw_data: dict[str, Any]) -> dict[str, Any]:
    """Ratio tiempo con voz / tiempo total (Transcribe)."""
    words = _transcribe_words(raw_data)
    if not words:
        return {
            "valor_numerico": 0,
            "unidad": "porcentaje",
            "confianza": None,
            "detalle": {
                "segundos_hablando": 0,
                "segundos_silencio": 0,
                "duracion_total_segundos": 0,
            },
        }

    # Fusiona palabras contiguas (gap <= SPEECH_GAP_S) en segmentos de habla.
    seg_start, seg_end = words[0]["start"], words[0]["end"]
    segundos_hablando = 0.0
    for w in words[1:]:
        if w["start"] - seg_end <= SPEECH_GAP_S:
            seg_end = max(seg_end, w["end"])
        else:
            segundos_hablando += seg_end - seg_start
            seg_start, seg_end = w["start"], w["end"]
    segundos_hablando += seg_end - seg_start
    segundos_hablando = round(segundos_hablando, 1)

    duracion_ms = _video_duration_ms(raw_data)
    duracion_total = round(duracion_ms / 1000 if duracion_ms else words[-1]["end"], 1)
    segundos_silencio = round(max(0.0, duracion_total - segundos_hablando), 1)
    pct = round(segundos_hablando / duracion_total * 100, 1) if duracion_total else 0

    return {
        "valor_numerico": pct,
        "unidad": "porcentaje",
        "confianza": None,
        "detalle": {
            "segundos_hablando": segundos_hablando,
            "segundos_silencio": segundos_silencio,
            "duracion_total_segundos": duracion_total,
        },
    }


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
