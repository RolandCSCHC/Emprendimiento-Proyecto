"""Amazon Bedrock — generación de texto para recomendaciones de profesores.

Usa la Converse API de bedrock-runtime, que es uniforme entre familias de
modelos (Amazon Nova, Anthropic, Llama, etc.). Por defecto se usa un modelo
nativo de AWS (Amazon Nova) para que el consumo lo cubran los créditos de AWS.
"""

from __future__ import annotations

import logging

from flask import current_app

from app.services.aws.boto_session import get_boto_client

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """BEDROCK_MODEL_ID u otra configuración requerida no está presente."""


class BedrockInvocationError(Exception):
    """Fallo en la invocación a AWS Bedrock (red, credenciales, throttling)."""


def invoke_model(prompt: str, max_tokens: int | None = None) -> str:
    """
    Invoca AWS Bedrock (Converse API) y devuelve el texto generado.

    Args:
        prompt: Texto del prompt a enviar al modelo.
        max_tokens: Máximo de tokens en la respuesta. Si es ``None`` se usa
            ``BEDROCK_MAX_TOKENS`` de la configuración.

    Returns:
        Texto generado por el modelo. String vacío si ``AWS_ENABLED`` es False
        (degradación elegante).

    Raises:
        ConfigurationError: Si ``BEDROCK_MODEL_ID`` no está configurado.
        BedrockInvocationError: Si la API de Bedrock falla.
    """
    config = current_app.config

    if not config.get("AWS_ENABLED"):
        logger.warning("AWS_ENABLED=False — Bedrock no se invoca, se omite recomendación.")
        return ""

    model_id = config.get("BEDROCK_MODEL_ID")
    if not model_id:
        raise ConfigurationError("BEDROCK_MODEL_ID no está configurado.")

    if max_tokens is None:
        max_tokens = config.get("BEDROCK_MAX_TOKENS", 1024)

    try:
        client = get_boto_client("bedrock-runtime")
        response = client.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": int(max_tokens), "temperature": 0.5},
        )
    except Exception as exc:  # boto3/botocore: credenciales, red, throttling
        logger.error("Fallo al invocar Bedrock (%s): %s", model_id, exc)
        raise BedrockInvocationError(str(exc)) from exc

    try:
        parts = response["output"]["message"]["content"]
        text = "".join(part.get("text", "") for part in parts)
    except (KeyError, TypeError) as exc:
        logger.error("Respuesta de Bedrock con formato inesperado: %s", exc)
        raise BedrockInvocationError("Respuesta de Bedrock con formato inesperado.") from exc

    return text.strip()
