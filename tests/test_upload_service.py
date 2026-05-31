"""Tests de la subida de clases (a S3 con AWS activo, local sin AWS)."""

from __future__ import annotations

import io

import pytest
from werkzeug.datastructures import FileStorage

from app.extensions import db
from app.models import AnalisisJob, Gimnasio, Metrica, Profesor, TipoClase
from app.services import upload_service


def _fake_video():
    return FileStorage(
        stream=io.BytesIO(b"contenido de video falso"),
        filename="clase.mp4",
        content_type="video/mp4",
    )


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
def no_enqueue(monkeypatch):
    """Evita que el pipeline real corra al crear la clase."""
    monkeypatch.setattr(upload_service, "enqueue_analysis", lambda clase_id: None)


def test_upload_con_aws_va_a_s3(app, db_session, no_enqueue, monkeypatch):
    app.config["AWS_ENABLED"] = True
    app.config["S3_BUCKET"] = "test-bucket"
    subido = {}
    monkeypatch.setattr(
        upload_service.s3_client,
        "upload_fileobj",
        lambda stream, bucket, key, content_type=None: subido.update(bucket=bucket, key=key),
    )
    g, p, t = _prereqs()
    db_session.commit()

    clase = upload_service.create_class_session(
        nombre="Clase S3", fecha="2026-05-04T09:00",
        gimnasio_id=str(g.id), profesor_id=str(p.id), tipo_clase_id=str(t.id),
        video=_fake_video(), audio=None,
    )

    arch = clase.archivos[0]
    assert arch.s3_bucket == "test-bucket"
    assert arch.s3_key == f"clases/{clase.id}/video.mp4"
    assert arch.ruta_local is None
    assert arch.tamano_bytes == len(b"contenido de video falso")
    assert subido["key"].startswith("clases/")
    # El pipeline es el dueño de los jobs: NO se pre-crean jobs pending.
    assert AnalisisJob.query.filter_by(clase_id=clase.id).count() == 0
    # Las 5 métricas sí se pre-crean (para el dashboard).
    assert Metrica.query.filter_by(clase_id=clase.id).count() == 5


def test_upload_sin_aws_guarda_local(app, db_session, no_enqueue, tmp_path):
    app.config["AWS_ENABLED"] = False
    app.config["UPLOAD_FOLDER"] = tmp_path
    g, p, t = _prereqs()
    db_session.commit()

    clase = upload_service.create_class_session(
        nombre="Clase local", fecha="2026-05-04T09:00",
        gimnasio_id=str(g.id), profesor_id=str(p.id), tipo_clase_id=str(t.id),
        video=_fake_video(), audio=None,
    )

    arch = clase.archivos[0]
    assert arch.ruta_local is not None
    assert arch.s3_key is None
    assert arch.s3_bucket is None
