"""Tests de apply_metrics_to_clase (requiere DB Postgres; ver db_session)."""

from __future__ import annotations

import pytest

from app.models import Metrica
from app.services.analysis import metrics_extractor
from app.services.analysis.constants import (
    CLASE_COMPLETADA,
    CLASE_COMPLETADA_PARCIAL,
    METRICA_COMPLETED,
    METRICA_FAILED,
    SERVICE_FACE_DETECTION,
    SERVICE_PERSON_TRACKING,
    SERVICE_TRANSCRIBE,
)
from tests.factories import crear_clase


def _word(start, end):
    return {
        "type": "pronunciation",
        "start_time": str(start),
        "end_time": str(end),
        "alternatives": [{"confidence": "0.95", "content": "x"}],
    }


def _combined():
    return {
        SERVICE_PERSON_TRACKING: {
            "persons": {"0": {"first_ms": 0, "last_ms": 10000, "conf": 0.95}},
            "video_duration_ms": 10000,
        },
        SERVICE_FACE_DETECTION: {
            "emotions": {"HAPPY": 90.0, "CALM": 10.0},
            "avg_confidence": 0.98,
        },
        SERVICE_TRANSCRIBE: {
            "transcript": "hola clase de pilates",
            "raw": {"results": {"items": [_word(i * 0.4, i * 0.4 + 0.3) for i in range(10)]}},
        },
    }


@pytest.fixture(autouse=True)
def mock_comprehend(monkeypatch):
    monkeypatch.setattr(
        metrics_extractor.comprehend_client,
        "analyze_sentiment",
        lambda text, lang: {
            "sentiment": "NEUTRAL",
            "scores": {"positive": 0.0, "negative": 0.0, "neutral": 1.0, "mixed": 0.0},
            "confidence": 0.0,
            "raw": None,
        },
    )


def test_todas_las_metricas_completan(app, db_session):
    clase = crear_clase(con_archivo=False)
    db_session.commit()

    metrics_extractor.apply_metrics_to_clase(str(clase.id), _combined())

    metricas = Metrica.query.filter_by(clase_id=clase.id).all()
    assert len(metricas) == 5
    assert all(m.status == METRICA_COMPLETED for m in metricas)
    db_session.refresh(clase)
    assert clase.status == CLASE_COMPLETADA


def test_un_fallo_deja_completada_parcial(app, db_session, monkeypatch):
    clase = crear_clase(con_archivo=False)
    db_session.commit()

    def _boom(_combined):
        raise ValueError("fallo simulado")

    monkeypatch.setitem(metrics_extractor.METRIC_EXTRACTORS, "asistencia", _boom)
    metrics_extractor.apply_metrics_to_clase(str(clase.id), _combined())

    db_session.refresh(clase)
    assert clase.status == CLASE_COMPLETADA_PARCIAL
    asistencia = Metrica.query.filter_by(clase_id=clase.id, clave="asistencia").first()
    assert asistencia.status == METRICA_FAILED


def test_upsert_no_duplica(app, db_session):
    clase = crear_clase(con_archivo=False)
    db_session.commit()

    metrics_extractor.apply_metrics_to_clase(str(clase.id), _combined())
    metrics_extractor.apply_metrics_to_clase(str(clase.id), _combined())

    assert Metrica.query.filter_by(clase_id=clase.id).count() == 5
