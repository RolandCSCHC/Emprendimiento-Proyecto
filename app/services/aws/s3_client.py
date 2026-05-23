"""Subida y lectura de archivos de media en Amazon S3."""

from __future__ import annotations

from typing import Optional

from app.models import ArchivoMedia


def upload_archivo_to_s3(archivo: ArchivoMedia, local_path: str) -> tuple[str, str]:
    """
    Sube un archivo local a S3 y devuelve (bucket, key).

    Pasos a implementar:
    1. Crear cliente boto3 S3 con credenciales de app.config.
    2. Generar s3_key: ej. ``clases/{clase_id}/{tipo}.{extension}``.
    3. Subir el fichero con ``upload_file`` o ``put_object``.
    4. Actualizar ``archivo.s3_bucket`` y ``archivo.s3_key`` en la sesión DB.

    Args:
        archivo: Registro ArchivoMedia asociado a la clase.
        local_path: Ruta absoluta del fichero en disco (UPLOAD_FOLDER).

    Returns:
        Tupla (bucket, key) del objeto subido.
    """
    raise NotImplementedError("Integración S3 pendiente. Ver README — Fase AWS.")


def get_s3_uri(bucket: str, key: str) -> str:
    """Devuelve la URI s3:// usada por Rekognition y Transcribe."""
    return f"s3://{bucket}/{key}"


def generate_presigned_url(bucket: str, key: str, expires_in: int = 3600) -> Optional[str]:
    """
    Opcional: URL firmada para descargar o previsualizar media desde el dashboard.

    Útil si no quieres servir archivos directamente desde Flask.
    """
    raise NotImplementedError("Integración S3 pendiente. Ver README — Fase AWS.")
