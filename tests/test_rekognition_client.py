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
    assert result["persons"] == {}


def test_get_person_tracking_aggregates_and_paginates(fake_client):
    # 2 páginas; persona 0 aparece en ms 0 y 5000 -> first/last agregados
    fake_client.get_person_tracking.side_effect = [
        {
            "JobStatus": "SUCCEEDED",
            "VideoMetadata": {"DurationMillis": 6000},
            "Persons": [{"Timestamp": 0, "Person": {"Index": 0, "Face": {"Confidence": 90}}}],
            "NextToken": "t",
        },
        {
            "JobStatus": "SUCCEEDED",
            "Persons": [
                {"Timestamp": 5000, "Person": {"Index": 0, "Face": {"Confidence": 90}}},
                {"Timestamp": 1000, "Person": {"Index": 1}},
            ],
        },
    ]
    result = rekognition_client.get_person_tracking_result("pt-123")
    assert result["status"] == "SUCCEEDED"
    assert result["video_duration_ms"] == 6000
    assert set(result["persons"].keys()) == {"0", "1"}
    assert result["persons"]["0"] == {"first_ms": 0, "last_ms": 5000, "conf": 0.9}


def test_get_face_detection_aggregates_emotions(fake_client):
    fake_client.get_face_detection.return_value = {
        "JobStatus": "SUCCEEDED",
        "Faces": [
            {"Face": {"Confidence": 98, "Emotions": [
                {"Type": "HAPPY", "Confidence": 80}, {"Type": "CALM", "Confidence": 20}]}},
            {"Face": {"Confidence": 96, "Emotions": [{"Type": "HAPPY", "Confidence": 60}]}},
        ],
    }
    result = rekognition_client.get_face_detection_result("fd-456")
    assert result["status"] == "SUCCEEDED"
    assert result["face_count"] == 2
    assert result["emotions"]["HAPPY"] == 140
    assert result["emotions"]["CALM"] == 20
    assert result["avg_confidence"] == 0.97


def test_get_face_detection_presencia_por_tercio(fake_client):
    fake_client.get_face_detection.return_value = {
        "JobStatus": "SUCCEEDED",
        "VideoMetadata": {"DurationMillis": 9000},
        "Faces": [
            {"Timestamp": 1000, "Face": {"Confidence": 99, "Emotions": []}},  # inicio: 2
            {"Timestamp": 1000, "Face": {"Confidence": 99, "Emotions": []}},
            {"Timestamp": 4000, "Face": {"Confidence": 99, "Emotions": []}},  # mitad: 3
            {"Timestamp": 4000, "Face": {"Confidence": 99, "Emotions": []}},
            {"Timestamp": 4000, "Face": {"Confidence": 99, "Emotions": []}},
            {"Timestamp": 8000, "Face": {"Confidence": 99, "Emotions": []}},  # final: 1
        ],
    }
    result = rekognition_client.get_face_detection_result("fd")
    assert result["video_duration_ms"] == 9000
    assert result["presencia"] == {"inicio": 2, "mitad": 3, "final": 1}


def test_get_face_detection_failed(fake_client):
    fake_client.get_face_detection.return_value = {
        "JobStatus": "FAILED",
        "StatusMessage": "algo salió mal",
        "Faces": [],
    }
    result = rekognition_client.get_face_detection_result("fd-456")
    assert result["status"] == "FAILED"
    assert result["error"] == "algo salió mal"
