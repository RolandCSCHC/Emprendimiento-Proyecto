"""Tests del Pipeline Orchestrator (requiere DB Postgres; ver db_session)."""

from __future__ import annotations

import pytest

from app.models import AnalisisJob
from app.services.analysis import pipeline
from app.services.analysis.constants import (
    CLASE_ANALIZANDO,
    JOB_FAILED,
    JOB_SUBMITTED,
    SERVICE_FACE_DETECTION,
    SERVICE_PERSON_TRACKING,
    SERVICE_TRANSCRIBE,
)
from tests.factories import crear_clase


@pytest.fixture
def mock_aws(monkeypatch):
    """Mockea los clientes AWS usados por el pipeline."""
    monkeypatch.setattr(pipeline.s3_client, "check_object_exists", lambda b, k: True)
    monkeypatch.setattr(
        pipeline.rekognition_client, "start_person_tracking",
        lambda b, k, sns=None: "pt-job",
    )
    monkeypatch.setattr(
        pipeline.rekognition_client, "start_face_detection",
        lambda b, k, sns=None: "fd-job",
    )
    monkeypatch.setattr(
        pipeline.transcribe_client, "start_transcription",
        lambda uri, lang=None, out=None, opts=None: "tr-job",
    )


def test_aws_disabled_is_noop(app, db_session):
    app.config["AWS_ENABLED"] = False
    clase = crear_clase()
    db_session.commit()

    pipeline.start_analysis_for_clase(str(clase.id))

    assert AnalisisJob.query.count() == 0


def test_video_launches_three_jobs(app, db_session, mock_aws):
    app.config["AWS_ENABLED"] = True
    clase = crear_clase(tipo_archivo="video")
    db_session.commit()

    pipeline.start_analysis_for_clase(str(clase.id))

    servicios = {j.servicio for j in AnalisisJob.query.all()}
    assert servicios == {SERVICE_PERSON_TRACKING, SERVICE_FACE_DETECTION, SERVICE_TRANSCRIBE}
    assert all(j.status == JOB_SUBMITTED for j in AnalisisJob.query.all())
    db_session.refresh(clase)
    assert clase.status == CLASE_ANALIZANDO


def test_audio_launches_only_transcribe(app, db_session, mock_aws):
    app.config["AWS_ENABLED"] = True
    clase = crear_clase(tipo_archivo="audio")
    db_session.commit()

    pipeline.start_analysis_for_clase(str(clase.id))

    jobs = AnalisisJob.query.all()
    assert len(jobs) == 1
    assert jobs[0].servicio == SERVICE_TRANSCRIBE


def test_archivo_without_s3_marks_failed(app, db_session, mock_aws):
    app.config["AWS_ENABLED"] = True
    clase = crear_clase(s3_bucket=None, s3_key=None)
    db_session.commit()

    pipeline.start_analysis_for_clase(str(clase.id))

    jobs = AnalisisJob.query.all()
    assert len(jobs) == 1
    assert jobs[0].status == JOB_FAILED


def test_s3_object_not_found_marks_failed(app, db_session, monkeypatch):
    app.config["AWS_ENABLED"] = True
    monkeypatch.setattr(pipeline.s3_client, "check_object_exists", lambda b, k: False)
    clase = crear_clase()
    db_session.commit()

    pipeline.start_analysis_for_clase(str(clase.id))

    jobs = AnalisisJob.query.all()
    assert len(jobs) == 1
    assert jobs[0].status == JOB_FAILED
