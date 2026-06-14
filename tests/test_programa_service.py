"""Tests de programas (clases recurrentes) y sesiones."""

from __future__ import annotations

import pytest

from app.extensions import db
from app.models import Clase, Gimnasio, Metrica, Profesor, ProgramaClase, TipoClase
from app.services import upload_service
from app.services.class_service import get_clase
from app.services.programa_service import (
    ProgramaValidationError,
    create_programa,
    delete_programa,
    get_programa,
    list_programas,
    list_sesiones,
)


def _prereqs():
    g = Gimnasio(nombre="Gym Test")
    db.session.add(g)
    db.session.flush()
    p = Profesor(gimnasio_id=g.id, nombre="Profe")
    t = TipoClase(gimnasio_id=g.id, nombre="Pilates")
    db.session.add_all([p, t])
    db.session.flush()
    return g, p, t


def test_create_programa(app, db_session):
    g, p, t = _prereqs()
    db_session.commit()

    programa = create_programa(
        nombre="Pilates martes",
        gimnasio_id=str(g.id),
        profesor_id=str(p.id),
        tipo_clase_id=str(t.id),
        sala="Sala 2",
    )

    assert programa.nombre == "Pilates martes"
    assert programa.sala == "Sala 2"
    assert ProgramaClase.query.count() == 1


def test_create_programa_requiere_nombre(app, db_session):
    g, p, t = _prereqs()
    db_session.commit()

    with pytest.raises(ProgramaValidationError):
        create_programa(
            nombre="  ",
            gimnasio_id=str(g.id),
            profesor_id=str(p.id),
            tipo_clase_id=str(t.id),
        )


def test_list_programas_con_conteo_sesiones(app, db_session, aws_on):
    g, p, t = _prereqs()
    db_session.commit()

    programa = create_programa(
        nombre="Pilates",
        gimnasio_id=str(g.id),
        profesor_id=str(p.id),
        tipo_clase_id=str(t.id),
    )

    for day in (4, 11, 18):
        upload_service.create_pending_session(
            programa_id=str(programa.id),
            fecha=f"2026-05-{day:02d}T09:00",
            video_filename="clase.mp4",
        )
        sesion = Clase.query.order_by(Clase.created_at.desc()).first()
        sesion.status = "pendiente_analisis"
        db.session.commit()

    programas = list_programas()
    assert len(programas) == 1
    assert programas[0].num_sesiones == 3


@pytest.fixture
def aws_on(app, monkeypatch):
    app.config["AWS_ENABLED"] = True
    app.config["S3_BUCKET"] = "test-bucket"
    monkeypatch.setattr(
        upload_service.s3_client,
        "generate_presigned_upload_url",
        lambda bucket, key, expires_in=None: f"https://s3.test/{bucket}/{key}?sig=x",
    )
    monkeypatch.setattr(upload_service, "enqueue_analysis", lambda clase_id: None)


def test_create_pending_session_vincula_programa(app, db_session, aws_on):
    g, p, t = _prereqs()
    db_session.commit()

    programa = create_programa(
        nombre="Pilates martes",
        gimnasio_id=str(g.id),
        profesor_id=str(p.id),
        tipo_clase_id=str(t.id),
    )

    result = upload_service.create_pending_session(
        programa_id=str(programa.id),
        fecha="2026-05-04T09:00",
        video_filename="semana1.mp4",
    )

    clase = get_clase(result["clase_id"])
    assert clase.programa_id == programa.id
    assert clase.gimnasio_id == g.id
    assert clase.profesor_id == p.id
    assert "Pilates martes" in clase.nombre
    assert Metrica.query.filter_by(clase_id=clase.id).count() == 5


def test_multiples_sesiones_mismo_programa(app, db_session, aws_on):
    g, p, t = _prereqs()
    db_session.commit()

    programa = create_programa(
        nombre="Pilates",
        gimnasio_id=str(g.id),
        profesor_id=str(p.id),
        tipo_clase_id=str(t.id),
    )

    ids = []
    for day in (4, 11, 18):
        result = upload_service.create_pending_session(
            programa_id=str(programa.id),
            fecha=f"2026-05-{day:02d}T09:00",
            video_filename="clase.mp4",
        )
        ids.append(result["clase_id"])
        sesion = get_clase(result["clase_id"])
        sesion.status = "completada"
        db.session.commit()

    sesiones = list_sesiones(programa.id)
    assert len(sesiones) == 3
    assert {str(s.id) for s in sesiones} == set(ids)


def test_delete_programa_elimina_sesiones(app, db_session, aws_on):
    g, p, t = _prereqs()
    db_session.commit()

    programa = create_programa(
        nombre="Pilates",
        gimnasio_id=str(g.id),
        profesor_id=str(p.id),
        tipo_clase_id=str(t.id),
    )
    upload_service.create_pending_session(
        programa_id=str(programa.id),
        fecha="2026-05-04T09:00",
        video_filename="clase.mp4",
    )
    sesion = Clase.query.first()
    sesion.status = "pendiente_analisis"
    db_session.commit()

    assert delete_programa(programa.id)
    assert ProgramaClase.query.count() == 0
    assert Clase.query.count() == 0


def test_analisis_sigue_por_sesion(app, db_session, monkeypatch):
    """El pipeline de análisis sigue operando por sesión (clase_id)."""
    from app.services import analysis_service
    from tests.factories import crear_clase

    app.config["AWS_ENABLED"] = False
    clase = crear_clase()
    db_session.commit()

    analysis_service.enqueue_analysis(str(clase.id))
    db_session.refresh(clase)
    assert clase.programa_id is not None
    assert get_programa(clase.programa_id) is not None
