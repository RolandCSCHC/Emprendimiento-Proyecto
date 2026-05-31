"""Helpers para crear registros de prueba en la DB."""

from __future__ import annotations

from datetime import datetime, timezone

from app.extensions import db
from app.models import ArchivoMedia, Clase, Gimnasio, Profesor, TipoClase


def crear_clase(
    *,
    con_archivo: bool = True,
    tipo_archivo: str = "video",
    s3_bucket: str | None = "bucket-test",
    s3_key: str | None = "video.mp4",
    status: str = "pendiente_analisis",
) -> Clase:
    """Crea un gimnasio/profesor/tipo/clase (y opcionalmente un archivo) y los persiste."""
    gimnasio = Gimnasio(nombre="Gym Test")
    db.session.add(gimnasio)
    db.session.flush()

    profesor = Profesor(gimnasio_id=gimnasio.id, nombre="Profe Test")
    tipo = TipoClase(gimnasio_id=gimnasio.id, nombre="Tipo Test")
    db.session.add_all([profesor, tipo])
    db.session.flush()

    clase = Clase(
        gimnasio_id=gimnasio.id,
        profesor_id=profesor.id,
        tipo_clase_id=tipo.id,
        nombre="Clase Test",
        fecha_inicio=datetime(2026, 5, 4, 9, 0, tzinfo=timezone.utc),
        status=status,
    )
    db.session.add(clase)
    db.session.flush()

    if con_archivo:
        db.session.add(
            ArchivoMedia(
                clase_id=clase.id,
                tipo=tipo_archivo,
                nombre_original="archivo.mp4",
                extension="mp4",
                s3_bucket=s3_bucket,
                s3_key=s3_key,
            )
        )
        db.session.flush()

    return clase
