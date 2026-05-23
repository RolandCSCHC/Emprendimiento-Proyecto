"""Amazon Comprehend — análisis de sentimiento del texto (opcional)."""

from __future__ import annotations

from typing import Any


def analyze_text_sentiment(text: str, language_code: str = "es") -> dict[str, Any]:
    """
    Analiza sentimiento del transcript (opcional para satisfaccion_alumno).

    Puede complementar Rekognition cuando solo tienes audio transcrito.
    No es obligatorio si Rekognition cubre engagement visual.

    Returns:
        Dict con scores de sentimiento y respuesta cruda de Comprehend.
    """
    raise NotImplementedError("Integración Comprehend pendiente. Ver README — Fase AWS.")
