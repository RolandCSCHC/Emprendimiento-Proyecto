"""Tests del Comprehend Client (mockeando el cliente boto3)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.services.aws import comprehend_client


@pytest.fixture
def fake_client(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr(comprehend_client, "get_boto_client", lambda service: client)
    return client


@pytest.mark.parametrize("text", ["", "   ", "corto"])
def test_empty_or_short_text_is_neutral(fake_client, text):
    result = comprehend_client.analyze_sentiment(text)
    assert result["sentiment"] == "NEUTRAL"
    assert result["confidence"] == 0.0
    assert result["raw"] is None
    fake_client.detect_sentiment.assert_not_called()


def test_normal_text_returns_scores(fake_client):
    fake_client.detect_sentiment.return_value = {
        "Sentiment": "POSITIVE",
        "SentimentScore": {
            "Positive": 0.9,
            "Negative": 0.02,
            "Neutral": 0.06,
            "Mixed": 0.02,
        },
    }
    result = comprehend_client.analyze_sentiment("la clase estuvo excelente hoy", "es")
    assert result["sentiment"] == "POSITIVE"
    assert result["scores"]["positive"] == 0.9
    assert result["confidence"] == 0.9
    assert result["raw"] is not None


def test_long_text_is_truncated(fake_client):
    fake_client.detect_sentiment.return_value = {"Sentiment": "NEUTRAL", "SentimentScore": {}}
    long_text = "a" * 6000
    comprehend_client.analyze_sentiment(long_text, "en")
    sent_text = fake_client.detect_sentiment.call_args.kwargs["Text"]
    assert len(sent_text.encode("utf-8")) <= comprehend_client.COMPREHEND_MAX_BYTES
