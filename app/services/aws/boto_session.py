"""Helper para instanciar clientes boto3 con la configuración de la app."""

from __future__ import annotations

from typing import Any

from flask import current_app


def get_boto_client(service_name: str) -> Any:
    """
    Crea un cliente boto3 para el servicio indicado usando la config de la app.

    Lee ``AWS_REGION`` y, si están presentes, ``AWS_ACCESS_KEY_ID`` /
    ``AWS_SECRET_ACCESS_KEY``. Si no hay access keys, boto3 usa su cadena de
    credenciales por defecto (rol IAM del entorno, perfil de AWS CLI, variables
    de entorno, etc.), tal como exige el requisito 14.4.

    El ``import boto3`` es perezoso para que la app funcione sin la dependencia
    instalada cuando ``AWS_ENABLED=false`` (degradación elegante, req. 14.2).

    Args:
        service_name: servicio AWS ('s3', 'rekognition', 'transcribe', 'comprehend').

    Returns:
        Cliente boto3 configurado.
    """
    import boto3

    config = current_app.config
    kwargs: dict[str, Any] = {"region_name": config.get("AWS_REGION")}

    access_key = config.get("AWS_ACCESS_KEY_ID")
    secret_key = config.get("AWS_SECRET_ACCESS_KEY")
    if access_key and secret_key:
        kwargs["aws_access_key_id"] = access_key
        kwargs["aws_secret_access_key"] = secret_key

    # S3 con SigV4: las URLs pre-firmadas solo firman el host (no el Content-Type),
    # para que el PUT directo desde el navegador no falle por el header que agrega.
    if service_name == "s3":
        from botocore.config import Config

        kwargs["config"] = Config(signature_version="s3v4")

    return boto3.client(service_name, **kwargs)
