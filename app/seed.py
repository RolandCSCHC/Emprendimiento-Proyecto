from __future__ import annotations

from app.extensions import db
from app.models import Gimnasio, Profesor, TipoClase


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

    profesores = [
        Profesor(
            gimnasio_id=gimnasio.id,
            nombre="María",
            apellido="González",
            email="maria.gonzalez@gymsight.demo",
            especialidades="yoga, pilates",
        ),
        Profesor(
            gimnasio_id=gimnasio.id,
            nombre="Carlos",
            apellido="Ruiz",
            email="carlos.ruiz@gymsight.demo",
            especialidades="spinning, funcional",
        ),
        Profesor(
            gimnasio_id=gimnasio.id,
            nombre="Ana",
            apellido="Silva",
            email="ana.silva@gymsight.demo",
            especialidades="pilates, stretching",
        ),
    ]
    db.session.add_all(profesores)

    tipos = [
        TipoClase(
            gimnasio_id=gimnasio.id,
            nombre="Yoga",
            descripcion="Clase grupal de yoga",
            duracion_tipica_min=60,
            capacidad_maxima=20,
        ),
        TipoClase(
            gimnasio_id=gimnasio.id,
            nombre="Pilates",
            descripcion="Pilates en colchoneta",
            duracion_tipica_min=55,
            capacidad_maxima=15,
        ),
        TipoClase(
            gimnasio_id=gimnasio.id,
            nombre="Spinning",
            descripcion="Ciclismo indoor",
            duracion_tipica_min=45,
            capacidad_maxima=25,
        ),
        TipoClase(
            gimnasio_id=gimnasio.id,
            nombre="Funcional",
            descripcion="Entrenamiento funcional grupal",
            duracion_tipica_min=50,
            capacidad_maxima=18,
        ),
    ]
    db.session.add_all(tipos)
    db.session.commit()
