from __future__ import annotations

import shutil
import uuid

from flask import current_app

from app.extensions import db
from app.models import AnalisisJob, Clase, Gimnasio, Metrica, Profesor, TipoClase


def list_gimnasios() -> list[Gimnasio]:
    return (
        Gimnasio.query.filter_by(activo=True)
        .order_by(Gimnasio.nombre)
        .all()
    )


def list_profesores(gimnasio_id: uuid.UUID | None = None) -> list[Profesor]:
    query = Profesor.query.filter_by(activo=True)
    if gimnasio_id:
        query = query.filter_by(gimnasio_id=gimnasio_id)
    return query.order_by(Profesor.nombre).all()


def list_tipos_clase(gimnasio_id: uuid.UUID | None = None) -> list[TipoClase]:
    query = TipoClase.query.filter_by(activo=True)
    if gimnasio_id:
        query = query.filter_by(gimnasio_id=gimnasio_id)
    return query.order_by(TipoClase.nombre).all()


def list_clases() -> list[Clase]:
    return (
        Clase.query.options(
            db.joinedload(Clase.profesor),
            db.joinedload(Clase.tipo_clase),
            db.joinedload(Clase.archivos),
        )
        .order_by(Clase.fecha_inicio.desc())
        .all()
    )


def get_clase(clase_id: str | uuid.UUID) -> Clase | None:
    if isinstance(clase_id, str):
        try:
            clase_id = uuid.UUID(clase_id)
        except ValueError:
            return None
    return (
        Clase.query.options(
            db.joinedload(Clase.gimnasio),
            db.joinedload(Clase.profesor),
            db.joinedload(Clase.tipo_clase),
            db.joinedload(Clase.archivos),
            db.joinedload(Clase.metricas),
            db.joinedload(Clase.analisis_jobs),
        )
        .filter_by(id=clase_id)
        .first()
    )


def create_pending_metrics(clase: Clase) -> list[Metrica]:
    metricas = []
    for key in current_app.config["METRIC_KEYS"]:
        metricas.append(Metrica(clase=clase, clave=key, status="pending"))
    return metricas


def create_pending_analysis_jobs(clase: Clase) -> list[AnalisisJob]:
    jobs = []
    for archivo in clase.archivos:
        servicio = "rekognition" if archivo.tipo == "video" else "transcribe"
        jobs.append(
            AnalisisJob(
                clase=clase,
                archivo=archivo,
                servicio=servicio,
                status="pending",
            )
        )
    return jobs


def _parse_clase_id(clase_id: str | uuid.UUID) -> uuid.UUID | None:
    if isinstance(clase_id, uuid.UUID):
        return clase_id
    try:
        return uuid.UUID(clase_id)
    except ValueError:
        return None


def delete_clase(clase_id: str | uuid.UUID) -> bool:
    parsed_id = _parse_clase_id(clase_id)
    if parsed_id is None:
        return False

    clase = get_clase(parsed_id)
    if clase is None:
        return False

    clase_dir = current_app.config["UPLOAD_FOLDER"] / str(clase.id)
    if clase_dir.exists():
        shutil.rmtree(clase_dir)

    db.session.delete(clase)
    db.session.commit()
    return True
