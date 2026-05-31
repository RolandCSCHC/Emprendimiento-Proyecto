"""Tests del Webhook SNS (requiere DB Postgres para la Notification)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from app.extensions import db
from app.models import AnalisisJob
from app.routes import webhooks
from app.services.analysis.constants import SERVICE_TRANSCRIBE
from tests.factories import crear_clase


@pytest.fixture
def sig_ok(monkeypatch):
    monkeypatch.setattr(webhooks, "_verify_sns_signature", lambda message: True)


@pytest.fixture
def fake_process(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr(webhooks, "process_completed_job", mock)
    return mock


def test_invalid_json_returns_400(client):
    resp = client.post("/webhooks/aws/sns", data="no-json")
    assert resp.status_code == 400


def test_invalid_signature_returns_403(client, monkeypatch):
    monkeypatch.setattr(webhooks, "_verify_sns_signature", lambda message: False)
    resp = client.post("/webhooks/aws/sns", data=json.dumps({"Type": "Notification"}))
    assert resp.status_code == 403


def test_subscription_confirmation(client, sig_ok, monkeypatch):
    fake_get = MagicMock()
    monkeypatch.setattr(webhooks.requests, "get", fake_get)
    body = {"Type": "SubscriptionConfirmation", "SubscribeURL": "https://sns.aws/confirm"}
    resp = client.post("/webhooks/aws/sns", data=json.dumps(body))
    assert resp.status_code == 200
    fake_get.assert_called_once_with("https://sns.aws/confirm", timeout=10)


def test_notification_processes_job(client, db_session, sig_ok, fake_process):
    clase = crear_clase(con_archivo=False)
    job = AnalisisJob(
        clase_id=clase.id,
        proveedor="aws",
        servicio=SERVICE_TRANSCRIBE,
        job_id_externo="ext-1",
        status="submitted",
    )
    db.session.add(job)
    db_session.commit()

    body = {
        "Type": "Notification",
        "Message": json.dumps({"JobId": "ext-1"}),
    }
    resp = client.post("/webhooks/aws/sns", data=json.dumps(body))

    assert resp.status_code == 200
    fake_process.assert_called_once_with(str(job.id))


def test_notification_without_job_id_returns_400(client, sig_ok, fake_process):
    body = {"Type": "Notification", "Message": json.dumps({"foo": "bar"})}
    resp = client.post("/webhooks/aws/sns", data=json.dumps(body))
    assert resp.status_code == 400
    fake_process.assert_not_called()


def test_notification_unknown_job_returns_400(client, db_session, sig_ok, fake_process):
    body = {"Type": "Notification", "Message": json.dumps({"JobId": "no-existe"})}
    resp = client.post("/webhooks/aws/sns", data=json.dumps(body))
    assert resp.status_code == 400
    fake_process.assert_not_called()
