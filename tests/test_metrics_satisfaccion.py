"""Tests del extractor de satisfacción del alumno (función pura)."""

from __future__ import annotations

from app.services.analysis.constants import SERVICE_FACE_DETECTION
from app.services.analysis.metrics_extractor import extract_satisfaccion_alumno


def _face(emotions, conf=98.0):
    return {
        "Timestamp": 0,
        "Face": {
            "Confidence": conf,
            "Emotions": [{"Type": t, "Confidence": c} for t, c in emotions],
        },
    }


def _combined(faces=None, comprehend=None):
    combined = {}
    if faces is not None:
        combined[SERVICE_FACE_DETECTION] = {"faces": faces}
    if comprehend is not None:
        combined["comprehend"] = comprehend
    return combined


def test_solo_visual_positivo():
    faces = [_face([("HAPPY", 90.0), ("CALM", 10.0)])]
    result = extract_satisfaccion_alumno(_combined(faces=faces))
    assert result["valor_numerico"] == 95
    assert result["detalle"]["peso_visual"] == 1.0
    assert result["detalle"]["score_textual"] is None


def test_visual_negativo():
    faces = [_face([("SAD", 80.0), ("ANGRY", 20.0)])]
    result = extract_satisfaccion_alumno(_combined(faces=faces))
    assert result["valor_numerico"] == 0


def test_visual_mas_textual():
    faces = [_face([("HAPPY", 90.0), ("CALM", 10.0)])]  # visual = 95
    comprehend = {
        "raw": {"x": 1},
        "scores": {"positive": 0.8, "negative": 0.1},
        "confidence": 0.8,
    }
    result = extract_satisfaccion_alumno(_combined(faces=faces, comprehend=comprehend))
    # 0.7*95 + 0.3*85 = 92
    assert result["valor_numerico"] == 92
    assert result["detalle"]["peso_visual"] == 0.7
    assert result["detalle"]["peso_textual"] == 0.3


def test_solo_textual_sin_rostros():
    comprehend = {
        "raw": {"x": 1},
        "scores": {"positive": 0.6, "negative": 0.2},
        "confidence": 0.6,
    }
    result = extract_satisfaccion_alumno(_combined(comprehend=comprehend))
    assert result["detalle"]["peso_textual"] == 1.0
    assert result["valor_numerico"] == 70  # 50 + 50*(0.6-0.2)


def test_sin_datos():
    result = extract_satisfaccion_alumno(_combined())
    assert result["valor_numerico"] == 0
    assert result["confianza"] == 0.0
    assert result["detalle"]["emociones"] == {}
