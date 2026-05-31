"""Tests de los extractores de asistencia y permanencia (funciones puras)."""

from __future__ import annotations

from app.services.analysis.constants import SERVICE_PERSON_TRACKING
from app.services.analysis.metrics_extractor import (
    extract_asistencia,
    extract_permanencia,
)


def _combined(persons, duration_ms=None):
    """persons: {indice: {first_ms, last_ms, conf}} (resumen compacto)."""
    return {
        SERVICE_PERSON_TRACKING: {"persons": persons, "video_duration_ms": duration_ms}
    }


def test_asistencia_sin_personas():
    result = extract_asistencia(_combined({}))
    assert result["valor_numerico"] == 0
    assert result["unidad"] == "personas"
    assert result["detalle"]["personas_detectadas"] == []


def test_asistencia_cuenta_personas_unicas():
    persons = {
        "0": {"first_ms": 0, "last_ms": 5000, "conf": 0.9},
        "1": {"first_ms": 1000, "last_ms": 4000, "conf": 0.9},
    }
    result = extract_asistencia(_combined(persons, duration_ms=10000))
    assert result["valor_numerico"] == 2
    assert result["confianza"] == 0.9


def test_permanencia_persona_completa():
    persons = {"0": {"first_ms": 0, "last_ms": 10000, "conf": 0.9}}
    result = extract_permanencia(_combined(persons, duration_ms=10000))
    assert result["valor_numerico"] == 100.0
    assert result["detalle"]["timeline"][0]["salida_ms"] is None


def test_permanencia_mixta():
    # persona 0: 0-10000 (100%), persona 1: 0-2000 (20%) -> 50% permaneció >=80%
    persons = {
        "0": {"first_ms": 0, "last_ms": 10000, "conf": 0.9},
        "1": {"first_ms": 0, "last_ms": 2000, "conf": 0.9},
    }
    result = extract_permanencia(_combined(persons, duration_ms=10000))
    assert result["valor_numerico"] == 50.0
    salidas = {p["person_index"]: p["salida_ms"] for p in result["detalle"]["timeline"]}
    assert salidas[0] is None
    assert salidas[1] == 2000


def test_permanencia_sin_datos():
    result = extract_permanencia(_combined({}))
    assert result["valor_numerico"] == 0
    assert result["detalle"]["timeline"] == []
