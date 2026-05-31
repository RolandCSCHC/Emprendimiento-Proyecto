"""Subida y lectura de archivos de media en Amazon S3."""

from __future__ import annotations

from flask import current_app

from app.services.aws.boto_session import get_s3_client


def generate_presigned_upload_url(bucket: str, key: str, expires_in: int | None = None) -> str:
    """Genera una URL firmada para PUT directo al objeto S3."""
    if expires_in is None:
        expires_in = current_app.config["PRESIGNED_URL_EXPIRES"]
    client = get_s3_client()
    return client.generate_presigned_url(
        "put_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in,
        HttpMethod="PUT",
    )


def check_object_exists(bucket: str, key: str) -> bool:
    """Devuelve True si el objeto existe en S3, False en 404."""
    import botocore.exceptions

    client = get_s3_client()
    try:
        client.head_object(Bucket=bucket, Key=key)
        return True
    except botocore.exceptions.ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code in ("404", "NoSuchKey", "NotFound"):
            return False
        raise


def get_s3_uri(bucket: str, key: str) -> str:
    """Devuelve la URI s3:// usada por Rekognition y Transcribe."""
    return f"s3://{bucket}/{key}"
