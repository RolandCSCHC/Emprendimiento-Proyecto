"""Lectura y validación de archivos de media en Amazon S3.

Los videos ya están en S3 (no se sube nada desde la app), así que este módulo
solo verifica existencia, construye URIs y genera URLs pre-firmadas.
"""

from __future__ import annotations

from typing import Optional

from botocore.exceptions import ClientError

from app.services.aws.boto_session import get_boto_client

# Códigos de error de S3/botocore que significan "el objeto no existe".
_NOT_FOUND_CODES = {"404", "NoSuchKey", "NotFound"}


def check_object_exists(bucket: str, key: str) -> bool:
    """
    Verifica que un objeto existe en S3 usando ``HeadObject``.

    Returns:
        ``True`` si el objeto existe, ``False`` si no se encontró (404).

    Raises:
        ClientError: ante cualquier otro error (permisos, bucket inexistente, etc.).
    """
    client = get_boto_client("s3")
    try:
        client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code in _NOT_FOUND_CODES:
            return False
        raise


def get_s3_uri(bucket: str, key: str) -> str:
    """Devuelve la URI ``s3://bucket/key`` usada por Rekognition y Transcribe."""
    return f"s3://{bucket}/{key}"


def generate_presigned_url(
    bucket: str, key: str, expires_in: int = 3600
) -> Optional[str]:
    """
    Genera una URL pre-firmada (``get_object``) para previsualizar el objeto.

    Args:
        bucket: bucket de S3.
        key: clave del objeto.
        expires_in: expiración en segundos (por defecto 3600).

    Returns:
        La URL pre-firmada, o ``None`` si ocurre un error.
    """
    client = get_boto_client("s3")
    try:
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_in,
        )
    except ClientError:
        return None
