"""Amazon Comprehend — análisis de sentimiento del texto transcrito.

Complementa la métrica de satisfacción del alumno (30% del score compuesto).
Es síncrono: no requiere polling. Se invoca desde el metrics_extractor.
"""

from __future__ import annotations

from typing import Any

from app.services.aws.boto_session import get_boto_client

# Comprehend acepta como máximo 5000 bytes UTF-8 por llamada a detect_sentiment.
COMPREHEND_MAX_BYTES = 5000
_MIN_CHARS = 10
_NEUTRAL_SCORES = {"positive": 0.0, "negative": 0.0, "neutral": 0.0, "mixed": 0.0}


def analyze_sentiment(text: str, language_code: str = "es") -> dict[str, Any]:
    """
    Analiza el sentimiento del texto con ``DetectSentiment``.

    Args:
        text: texto a analizar (transcripción).
        language_code: código de 2 letras de Comprehend (``es``, ``en``, ...).

    Returns:
        Dict con ``sentiment`` (POSITIVE|NEGATIVE|NEUTRAL|MIXED), ``scores``
        (positive/negative/neutral/mixed), ``confidence`` y ``raw``. Si el texto
        está vacío o es muy corto, retorna NEUTRAL con confianza 0.
    """
    if not text or len(text.strip()) < _MIN_CHARS:
        return {
            "sentiment": "NEUTRAL",
            "scores": dict(_NEUTRAL_SCORES),
            "confidence": 0.0,
            "raw": None,
        }

    # Truncar a 5000 bytes para respetar el límite de la API.
    encoded = text.encode("utf-8")
    if len(encoded) > COMPREHEND_MAX_BYTES:
        text = encoded[:COMPREHEND_MAX_BYTES].decode("utf-8", "ignore")

    client = get_boto_client("comprehend")
    response = client.detect_sentiment(Text=text, LanguageCode=language_code)

    score = response.get("SentimentScore", {})
    scores = {
        "positive": score.get("Positive", 0.0),
        "negative": score.get("Negative", 0.0),
        "neutral": score.get("Neutral", 0.0),
        "mixed": score.get("Mixed", 0.0),
    }
    sentiment = response.get("Sentiment", "NEUTRAL")
    return {
        "sentiment": sentiment,
        "scores": scores,
        "confidence": scores.get(sentiment.lower(), 0.0),
        "raw": response,
    }
