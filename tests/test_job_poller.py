"""Tests del Job Poller (requiere DB Postgres; ver db_session)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.extensions import db
from app.models import AnalisisJob
from app.services.analysis import job_poller
from app.services.analysis.constants import (
    CLASE_ERROR,
    JOB_COMPLETED,
    JOB_FAILED,
    JOB_IN_PROGRESS,
    JOB_SUBMITTED,
    SERVICE_TRANSCRIBE,
)
from tests.factories import crear_clase


def _crear_job(clase, servicio=SERVICE_TRANSCRIBE, status=JOB_SUBMITTED):
    job = AnalisisJob(
        clase_id=clase.id,
        proveedor="aws",
        servicio=servicio,
        job_id_externo="ext-123",
        status=status,
    )
    db.session.add(job)
    db.session.flush()
    return job


@pytest.fixture
def no_metrics(monkeypatch):
    """Evita ejecutar el extractor real (aún stub) y permite assertions."""
    mock = MagicMock()
    monkeypatch.setattr(job_poller, "apply_metrics_to_clase", mock)
    return mock


def test_in_progress_updates_status(app, db_session, no_metrics, monkeypatch):
    clase = crear_clase(con_archivo=False)
    job = _crear_job(clase)
    db_session.commit()
    monkeypatch.setitem(
        job_poller._GETTERS, SERVICE_TRANSCRIBE, lambda jid: {"status": "IN_PROGRESS"}
    )

    procesados = job_poller.poll_pending_jobs()

    assert procesados == 1
    db_session.refresh(job)
    assert job.status == JOB_IN_PROGRESS
    no_metrics.assert_not_called()


def test_completed_stores_raw_and_triggers_metrics(app, db_session, no_metrics, monkeypatch):
    clase = crear_clase(con_archivo=False)
    job = _crear_job(clase)
    db_session.commit()
    result = {"status": "SUCCEEDED", "transcript": "hola", "raw": {"x": 1}}
    monkeypatch.setitem(job_poller._GETTERS, SERVICE_TRANSCRIBE, lambda jid: result)

    job_poller.poll_pending_jobs()

    db_session.refresh(job)
    assert job.status == JOB_COMPLETED
    assert job.raw_response == result
    assert job.completed_at is not None
    no_metrics.assert_called_once()


def test_failed_sets_clase_error(app, db_session, no_metrics, monkeypatch):
    clase = crear_clase(con_archivo=False)
    job = _crear_job(clase)
    db_session.commit()
    monkeypatch.setitem(
        job_poller._GETTERS,
        SERVICE_TRANSCRIBE,
        lambda jid: {"status": "FAILED", "error": "boom"},
    )

    job_poller.poll_pending_jobs()

    db_session.refresh(job)
    db_session.refresh(clase)
    assert job.status == JOB_FAILED
    assert job.error_mensaje == "boom"
    assert clase.status == CLASE_ERROR
    no_metrics.assert_not_called()


def test_process_completed_job_single(app, db_session, no_metrics, monkeypatch):
    clase = crear_clase(con_archivo=False)
    job = _crear_job(clase)
    db_session.commit()
    monkeypatch.setitem(
        job_poller._GETTERS,
        SERVICE_TRANSCRIBE,
        lambda jid: {"status": "SUCCEEDED", "raw": {"ok": True}},
    )

    job_poller.process_completed_job(str(job.id))

    db_session.refresh(job)
    assert job.status == JOB_COMPLETED
    no_metrics.assert_called_once()
