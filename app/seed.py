from __future__ import annotations

from datetime import datetime, timedelta, timezone

from flask import current_app

from app.extensions import db
from app.models import ArchivoMedia, Clase, Gimnasio, Profesor, TipoClase

# Videos de demostración YA presentes en el bucket S3 (ver S3_BUCKET en .env).
# El instructor NO sube videos desde la app: la fuente ya está alimentada
# (grabaciones pasadas / cámaras). Aquí solo se enlazan los objetos S3 existentes.
# Nota: los 4 videos de demo están en inglés -> TRANSCRIBE_LANGUAGE_CODE=en-US.
DEMO_VIDEOS = [
    {
        "clase": "Mat Pilates en Vivo",
        "tipo_clase": "Pilates",
        "profesor": "María",
        "s3_key": "LIVE STREAM Recording of our Mat Pilates class - YOGAthletix (360p, h264).mp4",
    },
    {
        "clase": "Hot Pilates con Daniela",
        "tipo_clase": "Pilates",
        "profesor": "Ana",
        "s3_key": "One Hour Hot Pilates with Daniela - Yoga Flame (720p, h264).mp4",
    },
    {
        "clase": "Reformer Group Class",
        "tipo_clase": "Pilates",
        "profesor": "Ana",
        "s3_key": "Reformer Group Class - Authentic Pilates Learning Center (720p, h264).mp4",
    },
    {
        "clase": "Silver Sneakers con Mike",
        "tipo_clase": "Funcional",
        "profesor": "Carlos",
        "s3_key": "Silver Sneakers class with Mike every Friday at 10am #snapbc.mp4",
    },
]


def seed_database() -> None:
    if Gimnasio.query.first():
        return

    gimnasio = Gimnasio(
        nombre="Gymsight Demo",
        direccion="Av. Providencia 1234",
        ciudad="Santiago",
        email_contacto="contacto@gymsight.demo",
    )
    db.session.add(gimnasio)
    db.session.flush()

    profesores = {
        "María": Profesor(
            gimnasio_id=gimnasio.id,
            nombre="María",
            apellido="González",
            email="maria.gonzalez@gymsight.demo",
            especialidades="yoga, pilates",
        ),
        "Carlos": Profesor(
            gimnasio_id=gimnasio.id,
            nombre="Carlos",
            apellido="Ruiz",
            email="carlos.ruiz@gymsight.demo",
            especialidades="spinning, funcional",
        ),
        "Ana": Profesor(
            gimnasio_id=gimnasio.id,
            nombre="Ana",
            apellido="Silva",
            email="ana.silva@gymsight.demo",
            especialidades="pilates, stretching",
        ),
    }
    db.session.add_all(profesores.values())

    tipos = {
        "Yoga": TipoClase(
            gimnasio_id=gimnasio.id,
            nombre="Yoga",
            descripcion="Clase grupal de yoga",
            duracion_tipica_min=60,
            capacidad_maxima=20,
        ),
        "Pilates": TipoClase(
            gimnasio_id=gimnasio.id,
            nombre="Pilates",
            descripcion="Pilates en colchoneta",
            duracion_tipica_min=55,
            capacidad_maxima=15,
        ),
        "Spinning": TipoClase(
            gimnasio_id=gimnasio.id,
            nombre="Spinning",
            descripcion="Ciclismo indoor",
            duracion_tipica_min=45,
            capacidad_maxima=25,
        ),
        "Funcional": TipoClase(
            gimnasio_id=gimnasio.id,
            nombre="Funcional",
            descripcion="Entrenamiento funcional grupal",
            duracion_tipica_min=50,
            capacidad_maxima=18,
        ),
    }
    db.session.add_all(tipos.values())
    db.session.flush()

    _seed_clases_demo(gimnasio, profesores, tipos)

    db.session.commit()


def _seed_clases_demo(
    gimnasio: Gimnasio,
    profesores: dict[str, Profesor],
    tipos: dict[str, TipoClase],
) -> None:
    """Crea una clase por cada video de demo, enlazada a su objeto S3 existente."""
    bucket = current_app.config.get("S3_BUCKET") or ""
    base_fecha = datetime(2026, 5, 4, 9, 0, tzinfo=timezone.utc)

    for i, video in enumerate(DEMO_VIDEOS):
        clase = Clase(
            gimnasio_id=gimnasio.id,
            profesor_id=profesores[video["profesor"]].id,
            tipo_clase_id=tipos[video["tipo_clase"]].id,
            nombre=video["clase"],
            fecha_inicio=base_fecha + timedelta(days=i),
            status="pendiente_analisis",
        )
        db.session.add(clase)
        db.session.flush()

        db.session.add(
            ArchivoMedia(
                clase_id=clase.id,
                tipo="video",
                nombre_original=video["s3_key"],
                extension="mp4",
                s3_bucket=bucket,
                s3_key=video["s3_key"],
                mime_type="video/mp4",
            )
        )
