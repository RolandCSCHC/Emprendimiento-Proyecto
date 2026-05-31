"""Tests de claridad de instrucciones y tiempo hablando vs. demostrando."""

from __future__ import annotations

from app.services.analysis.constants import (
    SERVICE_PERSON_TRACKING,
    SERVICE_TRANSCRIBE,
)
from app.services.analysis.metrics_extractor import (
    extract_claridad_instrucciones,
    extract_tiempo_hablando_vs_demostrando,
)


def _word(content, start, end, conf=0.95):
    return {
        "type": "pronunciation",
        "start_time": str(start),
        "end_time": str(end),
        "alternatives": [{"confidence": str(conf), "content": content}],
    }


def _combined(items, duration_ms=None):
    combined = {SERVICE_TRANSCRIBE: {"raw": {"results": {"items": items}}}}
    if duration_ms is not None:
        combined[SERVICE_PERSON_TRACKING] = {
            "persons": {},
            "video_duration_ms": duration_ms,
        }
    return combined


# --- claridad --------------------------------------------------------------- #
def test_claridad_sin_palabras():
    result = extract_claridad_instrucciones(_combined([]))
    assert result["valor_numerico"] == 0
    assert result["detalle"]["palabras_por_minuto"] == 0


def test_claridad_ritmo_optimo():
    # 10 palabras en ~3.9s -> ~154 wpm (dentro del rango óptimo)
    items = [_word("p", i * 0.4, i * 0.4 + 0.3) for i in range(10)]
    result = extract_claridad_instrucciones(_combined(items))
    assert result["valor_numerico"] >= 90
    assert 120 <= result["detalle"]["palabras_por_minuto"] <= 160
    assert result["confianza"] == 0.95


def test_claridad_ritmo_lento():
    # 5 palabras en 60s -> ~5 wpm (muy bajo)
    items = [_word("p", i * 15.0, i * 15.0 + 0.5) for i in range(5)]
    result = extract_claridad_instrucciones(_combined(items))
    assert result["valor_numerico"] < 50


# --- tiempo hablando vs demostrando ---------------------------------------- #
def test_tiempo_sin_palabras():
    result = extract_tiempo_hablando_vs_demostrando(_combined([]))
    assert result["valor_numerico"] == 0


def test_tiempo_con_duracion_de_video():
    items = [_word("a", 0, 1), _word("b", 1.2, 2), _word("c", 5, 6)]
    result = extract_tiempo_hablando_vs_demostrando(_combined(items, duration_ms=10000))
    d = result["detalle"]
    assert d["segundos_hablando"] == 3.0
    assert d["duracion_total_segundos"] == 10.0
    assert d["segundos_silencio"] == 7.0
    assert result["valor_numerico"] == 30.0


def test_tiempo_sin_duracion_usa_ultima_palabra():
    items = [_word("a", 0, 1), _word("b", 1.2, 2), _word("c", 5, 6)]
    result = extract_tiempo_hablando_vs_demostrando(_combined(items))
    assert result["detalle"]["duracion_total_segundos"] == 6.0
    assert result["valor_numerico"] == 50.0
