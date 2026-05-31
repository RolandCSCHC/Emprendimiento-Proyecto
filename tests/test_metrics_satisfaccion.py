"""Tests del extractor de satisfacción del alumno (función pura)."""

from __future__ import annotations

from app.services.analysis.constants import SERVICE_FACE_DETECTION
from app.services.analysis.metrics_extractor import extract_satisfaccion_alumno


def _combined(emotions=None, avg_conf=None, comprehend=None):
    combined = {}
    if emotions is not None:
        combined[SERVICE_FACE_DETECTION] = {"emotions": emotions, "avg_confidence": avg_conf}
    if comprehend is not None:
        combined["comprehend"] = comprehend
    return combined


def test_solo_visual_positivo():
    result = extract_satisfaccion_alumno(_combined({"HAPPY": 90.0, "CALM": 10.0}, avg_conf=0.98))
    assert result["valor_numerico"] == 95
    assert result["detalle"]["peso_visual"] == 1.0
    assert result["detalle"]["score_textual"] is None
    assert result["confianza"] == 0.98


def test_visual_negativo():
    result = extract_satisfaccion_alumno(_combined({"SAD": 80.0, "ANGRY": 20.0}, avg_conf=0.9))
    assert result["valor_numerico"] == 0


def test_visual_mas_textual():
    comprehend = {"raw": {"x": 1}, "scores": {"positive": 0.8, "negative": 0.1}, "confidence": 0.8}
    result = extract_satisfaccion_alumno(
        _combined({"HAPPY": 90.0, "CALM": 10.0}, avg_conf=0.98, comprehend=comprehend)
    )
    # 0.7*95 + 0.3*85 = 92
    assert result["valor_numerico"] == 92
    assert result["detalle"]["peso_visual"] == 0.7
    assert result["detalle"]["peso_textual"] == 0.3


def test_solo_textual_sin_rostros():
    comprehend = {"raw": {"x": 1}, "scores": {"positive": 0.6, "negative": 0.2}, "confidence": 0.6}
    result = extract_satisfaccion_alumno(_combined(comprehend=comprehend))
    assert result["detalle"]["peso_textual"] == 1.0
    assert result["valor_numerico"] == 70  # 50 + 50*(0.6-0.2)


def test_sin_datos():
    result = extract_satisfaccion_alumno(_combined())
    assert result["valor_numerico"] == 0
    assert result["confianza"] == 0.0
    assert result["detalle"]["emociones"] == {}
