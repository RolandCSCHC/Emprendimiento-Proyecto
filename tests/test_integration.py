"""
Verificación end-to-end del pipeline (Task 16).

- AWS deshabilitado: enqueue es no-op y la app arranca sin credenciales.
- CLI `flask aws-poll-jobs` ejecuta sin error.
- Flujo completo (enqueue → poll → métricas → estado final) con AWS mockeado.
"""

from __future__ import annotations

from app.models import AnalisisJob, Metrica
from app.services import analysis_service
from app.services.analysis import job_poller, metrics_extractor, pipeline
from app.services.analysis.constants import (
    CLASE_COMPLETADA,
    METRICA_COMPLETED,
    SERVICE_FACE_DETECTION,
    SERVICE_PERSON_TRACKING,
    SERVICE_TRANSCRIBE,
)
from tests.factories import crear_clase


def test_aws_disabled_enqueue_es_noop(app, db_session):
    app.config["AWS_ENABLED"] = False
    clase = crear_clase()
    db_session.commit()

    analysis_service.enqueue_analysis(str(clase.id))

    assert AnalisisJob.query.count() == 0
    db_session.refresh(clase)
    assert clase.status == "pendiente_analisis"


def test_cli_poll_jobs_sin_jobs(app, db_session):
    result = app.test_cli_runner().invoke(args=["aws-poll-jobs"])
    assert result.exit_code == 0
    assert "Jobs procesados: 0" in result.output


def _word(i):
    return {
        "type": "pronunciation",
        "start_time": str(i * 0.4),
        "end_time": str(i * 0.4 + 0.3),
        "alternatives": [{"confidence": "0.95", "content": "x"}],
    }


def test_flujo_completo(app, db_session, monkeypatch):
    app.config["AWS_ENABLED"] = True

    # --- enqueue: mockear S3 + lanzamientos ---
    monkeypatch.setattr(pipeline.s3_client, "check_object_exists", lambda b, k: True)
    monkeypatch.setattr(
        pipeline.rekognition_client, "start_person_tracking", lambda b, k, sns=None: "pt"
    )
    monkeypatch.setattr(
        pipeline.rekognition_client, "start_face_detection", lambda b, k, sns=None: "fd"
    )
    monkeypatch.setattr(
        pipeline.transcribe_client, "start_transcription",
        lambda uri, lang=None, out=None, opts=None: "tr",
    )

    clase = crear_clase(tipo_archivo="video")
    db_session.commit()

    analysis_service.enqueue_analysis(str(clase.id))
    assert AnalisisJob.query.filter_by(clase_id=clase.id).count() == 3

    # --- poll: mockear getters (todos SUCCEEDED) y Comprehend ---
    pt_result = {
        "status": "SUCCEEDED",
        "persons": {"0": {"first_ms": 0, "last_ms": 10000, "conf": 0.95}},
        "video_duration_ms": 10000,
    }
    fd_result = {
        "status": "SUCCEEDED",
        "emotions": {"HAPPY": 90.0, "CALM": 10.0},
        "avg_confidence": 0.98,
    }
    tr_result = {
        "status": "SUCCEEDED",
        "transcript": "hola clase de pilates",
        "raw": {"results": {"items": [_word(i) for i in range(10)]}},
    }
    monkeypatch.setitem(job_poller._GETTERS, SERVICE_PERSON_TRACKING, lambda jid: pt_result)
    monkeypatch.setitem(job_poller._GETTERS, SERVICE_FACE_DETECTION, lambda jid: fd_result)
    monkeypatch.setitem(job_poller._GETTERS, SERVICE_TRANSCRIBE, lambda jid: tr_result)
    monkeypatch.setattr(
        metrics_extractor.comprehend_client, "analyze_sentiment",
        lambda text, lang: {
            "sentiment": "NEUTRAL",
            "scores": {"positive": 0.0, "negative": 0.0, "neutral": 1.0, "mixed": 0.0},
            "confidence": 0.0,
            "raw": None,
        },
    )

    procesados = job_poller.poll_pending_jobs()
    assert procesados == 3

    metricas = Metrica.query.filter_by(clase_id=clase.id).all()
    assert len(metricas) == 5
    assert all(m.status == METRICA_COMPLETED for m in metricas)
    db_session.refresh(clase)
    assert clase.status == CLASE_COMPLETADA
