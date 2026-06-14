"""Helpers para crear registros de prueba en la DB."""

from __future__ import annotations

from datetime import datetime, timezone

from app.extensions import db
from app.models import ArchivoMedia, Clase, Gimnasio, Profesor, ProgramaClase, TipoClase


def crear_programa(
    *,
    nombre: str = "Clase Test",
    gimnasio: Gimnasio | None = None,
    profesor: Profesor | None = None,
    tipo: TipoClase | None = None,
) -> ProgramaClase:
    """Crea gimnasio/profesor/tipo/programa si no se pasan."""
    if gimnasio is None:
        gimnasio = Gimnasio(nombre="Gym Test")
        db.session.add(gimnasio)
        db.session.flush()

    if profesor is None:
        profesor = Profesor(gimnasio_id=gimnasio.id, nombre="Profe Test")
        db.session.add(profesor)
        db.session.flush()

    if tipo is None:
        tipo = TipoClase(gimnasio_id=gimnasio.id, nombre="Tipo Test")
        db.session.add(tipo)
        db.session.flush()

    programa = ProgramaClase(
        gimnasio_id=gimnasio.id,
        profesor_id=profesor.id,
        tipo_clase_id=tipo.id,
        nombre=nombre,
    )
    db.session.add(programa)
    db.session.flush()
    return programa


def crear_clase(
    *,
    con_archivo: bool = True,
    tipo_archivo: str = "video",
    s3_bucket: str | None = "bucket-test",
    s3_key: str | None = "video.mp4",
    status: str = "pendiente_analisis",
    programa: ProgramaClase | None = None,
) -> Clase:
    """Crea un programa/sesión (y opcionalmente un archivo) y los persiste."""
    if programa is None:
        programa = crear_programa()

    fecha = datetime(2026, 5, 4, 9, 0, tzinfo=timezone.utc)
    clase = Clase(
        gimnasio_id=programa.gimnasio_id,
        profesor_id=programa.profesor_id,
        tipo_clase_id=programa.tipo_clase_id,
        programa_id=programa.id,
        nombre=f"{programa.nombre} — {fecha.strftime('%d/%m/%Y %H:%M')}",
        fecha_inicio=fecha,
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
