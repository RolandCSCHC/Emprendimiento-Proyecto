"""Tests del Transcribe Client (mockeando el cliente boto3 y la descarga HTTP)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.services.aws import transcribe_client


@pytest.fixture
def fake_client(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr(transcribe_client, "get_boto_client", lambda service: client)
    return client


@pytest.mark.parametrize("language_code", ["es-ES", "en-US", "pt-BR"])
def test_start_transcription_forwards_language(fake_client, language_code):
    job_name = transcribe_client.start_transcription(
        "s3://bucket/video.mp4", language_code=language_code
    )
    assert job_name.startswith("gymsight-")
    kwargs = fake_client.start_transcription_job.call_args.kwargs
    assert kwargs["LanguageCode"] == language_code
    assert kwargs["Media"] == {"MediaFileUri": "s3://bucket/video.mp4"}
    assert kwargs["MediaFormat"] == "mp4"
    assert "IdentifyLanguage" not in kwargs


@pytest.mark.parametrize("lang", [None, "auto"])
def test_start_transcription_auto_detecta_idioma(fake_client, lang):
    transcribe_client.start_transcription(
        "s3://bucket/video.mp4", language_code=lang, language_options=["es-ES", "en-US"]
    )
    kwargs = fake_client.start_transcription_job.call_args.kwargs
    assert kwargs["IdentifyLanguage"] is True
    assert kwargs["LanguageOptions"] == ["es-ES", "en-US"]
    assert "LanguageCode" not in kwargs


def test_get_transcription_in_progress(fake_client):
    fake_client.get_transcription_job.return_value = {
        "TranscriptionJob": {"TranscriptionJobStatus": "IN_PROGRESS"}
    }
    result = transcribe_client.get_transcription_result("job-1")
    assert result["status"] == "IN_PROGRESS"
    assert result["transcript"] is None


def test_get_transcription_completed(fake_client, monkeypatch):
    fake_client.get_transcription_job.return_value = {
        "TranscriptionJob": {
            "TranscriptionJobStatus": "COMPLETED",
            "LanguageCode": "es-ES",
            "Transcript": {"TranscriptFileUri": "https://example/out.json"},
        }
    }
    payload = {"results": {"transcripts": [{"transcript": "hola clase"}], "items": []}}
    fake_response = MagicMock()
    fake_response.json.return_value = payload
    monkeypatch.setattr(transcribe_client.requests, "get", lambda *a, **k: fake_response)

    result = transcribe_client.get_transcription_result("job-1")
    assert result["status"] == "SUCCEEDED"
    assert result["transcript"] == "hola clase"
    assert result["raw"] == payload
    assert result["language_code"] == "es-ES"  # idioma detectado


def test_get_transcription_failed(fake_client):
    fake_client.get_transcription_job.return_value = {
        "TranscriptionJob": {
            "TranscriptionJobStatus": "FAILED",
            "FailureReason": "formato no soportado",
        }
    }
    result = transcribe_client.get_transcription_result("job-1")
    assert result["status"] == "FAILED"
    assert result["error"] == "formato no soportado"
