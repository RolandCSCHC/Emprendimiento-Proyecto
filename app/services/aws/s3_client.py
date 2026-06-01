"""Lectura, subida y validación de archivos de media en Amazon S3."""

from __future__ import annotations

from typing import Any, Optional

from botocore.exceptions import ClientError
from flask import current_app

from app.services.aws.boto_session import get_boto_client

# Códigos de error de S3/botocore que significan "el objeto no existe".
_NOT_FOUND_CODES = {"404", "NoSuchKey", "NotFound"}


def upload_fileobj(fileobj: Any, bucket: str, key: str, content_type: Optional[str] = None) -> tuple[str, str]:
    """
    Sube un archivo (stream/FileStorage) a S3 sin pasar por disco.

    Args:
        fileobj: objeto tipo archivo (p. ej. ``werkzeug FileStorage`` o ``.stream``).
        bucket: bucket destino.
        key: clave del objeto en S3.
        content_type: MIME opcional para guardarlo como metadato.

    Returns:
        Tupla ``(bucket, key)`` del objeto subido.
    """
    client = get_boto_client("s3")
    extra_args = {"ContentType": content_type} if content_type else None
    client.upload_fileobj(fileobj, bucket, key, ExtraArgs=extra_args)
    return bucket, key


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


def generate_presigned_upload_url(
    bucket: str, key: str, expires_in: Optional[int] = None
) -> str:
    """
    Genera una URL pre-firmada para **subir (PUT)** un objeto directo a S3 desde
    el navegador (el archivo no pasa por el servidor).
    """
    if expires_in is None:
        expires_in = current_app.config.get("PRESIGNED_URL_EXPIRES", 900)
    client = get_boto_client("s3")
    return client.generate_presigned_url(
        "put_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in,
        HttpMethod="PUT",
    )


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
