"""Tests de los extractores de asistencia y permanencia (funciones puras)."""

from __future__ import annotations

from app.services.analysis.constants import SERVICE_PERSON_TRACKING
from app.services.analysis.metrics_extractor import (
    extract_asistencia,
    extract_permanencia,
)


def _det(index, ts, conf=90.0):
    return {"Timestamp": ts, "Person": {"Index": index, "Face": {"Confidence": conf}}}


def _combined(persons, duration=None):
    raw = {"VideoMetadata": {"DurationMillis": duration}} if duration else {}
    return {SERVICE_PERSON_TRACKING: {"persons": persons, "raw": raw}}


def test_asistencia_sin_personas():
    result = extract_asistencia(_combined([]))
    assert result["valor_numerico"] == 0
    assert result["unidad"] == "personas"
    assert result["detalle"]["personas_detectadas"] == []


def test_asistencia_cuenta_personas_unicas():
    persons = [_det(0, 0), _det(0, 5000), _det(1, 1000)]
    result = extract_asistencia(_combined(persons, duration=10000))
    assert result["valor_numerico"] == 2
    assert result["confianza"] == 0.9  # 90/100


def test_permanencia_persona_completa():
    persons = [_det(0, 0), _det(0, 10000)]
    result = extract_permanencia(_combined(persons, duration=10000))
    assert result["valor_numerico"] == 100.0
    assert result["detalle"]["timeline"][0]["salida_ms"] is None


def test_permanencia_mixta():
    # persona 0: 0-10000 (100%), persona 1: 0-2000 (20%) -> 50% permaneció >=80%
    persons = [_det(0, 0), _det(0, 10000), _det(1, 0), _det(1, 2000)]
    result = extract_permanencia(_combined(persons, duration=10000))
    assert result["valor_numerico"] == 50.0
    salidas = {p["person_index"]: p["salida_ms"] for p in result["detalle"]["timeline"]}
    assert salidas[0] is None
    assert salidas[1] == 2000


def test_permanencia_sin_datos():
    result = extract_permanencia(_combined([]))
    assert result["valor_numerico"] == 0
    assert result["detalle"]["timeline"] == []
