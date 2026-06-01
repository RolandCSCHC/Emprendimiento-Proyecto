"""Tests del flujo de subida directa cliente → S3 (presigned)."""

from __future__ import annotations

import pytest

from app.extensions import db
from app.models import AnalisisJob, Gimnasio, Metrica, Profesor, TipoClase
from app.services import upload_service
from app.services.class_service import get_clase


def _prereqs():
    g = Gimnasio(nombre="Gym Test")
    db.session.add(g)
    db.session.flush()
    p = Profesor(gimnasio_id=g.id, nombre="Profe")
    t = TipoClase(gimnasio_id=g.id, nombre="Tipo")
    db.session.add_all([p, t])
    db.session.flush()
    return g, p, t


@pytest.fixture
def aws_on(app, monkeypatch):
    app.config["AWS_ENABLED"] = True
    app.config["S3_BUCKET"] = "test-bucket"
    monkeypatch.setattr(
        upload_service.s3_client, "generate_presigned_upload_url",
        lambda bucket, key, expires_in=None: f"https://s3.test/{bucket}/{key}?sig=x",
    )
    monkeypatch.setattr(upload_service, "enqueue_analysis", lambda clase_id: None)


def test_create_pending_devuelve_presigned_y_no_jobs(app, db_session, aws_on):
    g, p, t = _prereqs()
    db_session.commit()

    result = upload_service.create_pending_class(
        nombre="Clase", fecha="2026-05-04T09:00",
        gimnasio_id=str(g.id), profesor_id=str(p.id), tipo_clase_id=str(t.id),
        video_filename="clase.mp4",
    )

    assert "video" in result["uploads"]
    assert result["uploads"]["video"]["presigned_url"].startswith("https://s3.test/")
    assert result["uploads"]["video"]["s3_key"].endswith("video.mp4")

    clase = get_clase(result["clase_id"])
    assert clase.status == "awaiting_upload"
    arch = clase.archivos[0]
    assert arch.s3_key == result["uploads"]["video"]["s3_key"]
    assert arch.ruta_local is None
    # El pipeline es dueño de los jobs: no se pre-crean. Métricas sí (para el dashboard).
    assert AnalisisJob.query.filter_by(clase_id=clase.id).count() == 0
    assert Metrica.query.filter_by(clase_id=clase.id).count() == 5


def test_finalize_marca_lista_y_dispara_analisis(app, db_session, aws_on, monkeypatch):
    g, p, t = _prereqs()
    db_session.commit()
    result = upload_service.create_pending_class(
        nombre="Clase", fecha="2026-05-04T09:00",
        gimnasio_id=str(g.id), profesor_id=str(p.id), tipo_clase_id=str(t.id),
        video_filename="clase.mp4",
    )
    llamadas = []
    monkeypatch.setattr(upload_service, "enqueue_analysis", lambda cid: llamadas.append(cid))
    monkeypatch.setattr(upload_service.s3_client, "check_object_exists", lambda b, k: True)

    clase = upload_service.finalize_class_upload(result["clase_id"])

    assert clase.status == "pendiente_analisis"
    assert llamadas == [result["clase_id"]]


def test_finalize_falla_si_falta_objeto_en_s3(app, db_session, aws_on, monkeypatch):
    g, p, t = _prereqs()
    db_session.commit()
    result = upload_service.create_pending_class(
        nombre="Clase", fecha="2026-05-04T09:00",
        gimnasio_id=str(g.id), profesor_id=str(p.id), tipo_clase_id=str(t.id),
        video_filename="clase.mp4",
    )
    monkeypatch.setattr(upload_service.s3_client, "check_object_exists", lambda b, k: False)

    with pytest.raises(upload_service.UploadValidationError):
        upload_service.finalize_class_upload(result["clase_id"])
