"""Tests del Rekognition Client (mockeando el cliente boto3)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.services.aws import rekognition_client


@pytest.fixture
def fake_client(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr(rekognition_client, "get_boto_client", lambda service: client)
    return client


def test_start_person_tracking_returns_job_id(fake_client):
    fake_client.start_person_tracking.return_value = {"JobId": "pt-123"}
    job_id = rekognition_client.start_person_tracking("bucket", "video.mp4")
    assert job_id == "pt-123"
    args = fake_client.start_person_tracking.call_args.kwargs
    assert args["Video"]["S3Object"] == {"Bucket": "bucket", "Name": "video.mp4"}
    assert "NotificationChannel" not in args  # sin SNS por defecto


def test_start_face_detection_uses_all_attributes(fake_client):
    fake_client.start_face_detection.return_value = {"JobId": "fd-456"}
    job_id = rekognition_client.start_face_detection("bucket", "video.mp4")
    assert job_id == "fd-456"
    assert fake_client.start_face_detection.call_args.kwargs["FaceAttributes"] == "ALL"


def test_get_person_tracking_in_progress(fake_client):
    fake_client.get_person_tracking.return_value = {
        "JobStatus": "IN_PROGRESS",
        "Persons": [],
    }
    result = rekognition_client.get_person_tracking_result("pt-123")
    assert result["status"] == "IN_PROGRESS"
    assert result["persons"] == []


def test_get_person_tracking_paginates(fake_client):
    fake_client.get_person_tracking.side_effect = [
        {"JobStatus": "SUCCEEDED", "Persons": [{"Person": {"Index": 0}}], "NextToken": "t"},
        {"JobStatus": "SUCCEEDED", "Persons": [{"Person": {"Index": 1}}]},
    ]
    result = rekognition_client.get_person_tracking_result("pt-123")
    assert result["status"] == "SUCCEEDED"
    assert len(result["persons"]) == 2
    assert "NextToken" not in result["raw"]


def test_get_face_detection_failed(fake_client):
    fake_client.get_face_detection.return_value = {
        "JobStatus": "FAILED",
        "StatusMessage": "algo salió mal",
        "Faces": [],
    }
    result = rekognition_client.get_face_detection_result("fd-456")
    assert result["status"] == "FAILED"
    assert result["error"] == "algo salió mal"
