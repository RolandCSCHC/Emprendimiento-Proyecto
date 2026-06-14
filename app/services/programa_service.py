from __future__ import annotations

import shutil
import uuid
from typing import Any

from flask import current_app

from app.extensions import db
from app.models import Clase, ProgramaClase

SESSION_CHART_STATUSES = ("completada", "completada_parcial")


class ProgramaValidationError(Exception):
    pass


def _parse_uuid(value: str, message: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise ProgramaValidationError(message) from exc


def list_programas() -> list[ProgramaClase]:
    return (
        ProgramaClase.query.options(
            db.joinedload(ProgramaClase.profesor),
            db.joinedload(ProgramaClase.tipo_clase),
            db.joinedload(ProgramaClase.sesiones),
        )
        .filter_by(activo=True)
        .order_by(ProgramaClase.nombre)
        .all()
    )


def get_programa(programa_id: str | uuid.UUID) -> ProgramaClase | None:
    if isinstance(programa_id, str):
        try:
            programa_id = uuid.UUID(programa_id)
        except ValueError:
            return None
    return (
        ProgramaClase.query.options(
            db.joinedload(ProgramaClase.gimnasio),
            db.joinedload(ProgramaClase.profesor),
            db.joinedload(ProgramaClase.tipo_clase),
            db.joinedload(ProgramaClase.sesiones).joinedload(Clase.archivos),
            db.joinedload(ProgramaClase.sesiones).joinedload(Clase.metricas),
        )
        .filter_by(id=programa_id, activo=True)
        .first()
    )


def create_programa(
    *,
    nombre: str,
    gimnasio_id: str,
    profesor_id: str,
    tipo_clase_id: str,
    sala: str | None = None,
    nivel: str | None = None,
    notas: str | None = None,
) -> ProgramaClase:
    if not nombre.strip():
        raise ProgramaValidationError("El nombre de la clase es obligatorio.")

    gimnasio_uuid = _parse_uuid(gimnasio_id, "Selecciona un gimnasio válido.")
    profesor_uuid = _parse_uuid(profesor_id, "Selecciona un profesor válido.")
    tipo_clase_uuid = _parse_uuid(tipo_clase_id, "Selecciona un tipo de clase válido.")

    programa = ProgramaClase(
        gimnasio_id=gimnasio_uuid,
        profesor_id=profesor_uuid,
        tipo_clase_id=tipo_clase_uuid,
        nombre=nombre.strip(),
        sala=sala.strip() if sala else None,
        nivel=nivel.strip() if nivel else None,
        notas=notas.strip() if notas else None,
    )
    db.session.add(programa)
    db.session.commit()
    return programa


def list_sesiones(programa_id: str | uuid.UUID) -> list[Clase]:
    parsed_id = _parse_uuid(str(programa_id), "Programa no válido.")
    return (
        Clase.query.options(
            db.joinedload(Clase.archivos),
            db.joinedload(Clase.metricas),
        )
        .filter(
            Clase.programa_id == parsed_id,
            Clase.status != "awaiting_upload",
        )
        .order_by(Clase.fecha_inicio.desc())
        .all()
    )


def get_programa_metric_series(programa_id: str | uuid.UUID) -> dict[str, list[dict[str, Any]]]:
    """Series temporales por métrica (fecha de sesión → valor numérico)."""
    parsed_id = _parse_uuid(str(programa_id), "Programa no válido.")
    metric_keys = current_app.config["METRIC_KEYS"]

    sesiones = (
        Clase.query.options(db.joinedload(Clase.metricas))
        .filter(
            Clase.programa_id == parsed_id,
            Clase.status.in_(SESSION_CHART_STATUSES),
        )
        .order_by(Clase.fecha_inicio.asc())
        .all()
    )

    series: dict[str, list[dict[str, Any]]] = {key: [] for key in metric_keys}
    for sesion in sesiones:
        metricas_by_key = {m.clave: m for m in sesion.metricas}
        fecha = sesion.fecha_inicio.strftime("%d/%m/%Y")
        for key in metric_keys:
            metrica = metricas_by_key.get(key)
            if (
                metrica
                and metrica.status == "completed"
                and metrica.valor_numerico is not None
            ):
                series[key].append(
                    {"fecha": fecha, "valor": float(metrica.valor_numerico)}
                )
    return series


def chart_point_count(chart_series: dict[str, list[dict[str, Any]]]) -> int:
    """Número máximo de puntos en cualquier serie (para mensajes de UI)."""
    if not chart_series:
        return 0
    return max((len(points) for points in chart_series.values()), default=0)


def delete_programa(programa_id: str | uuid.UUID) -> bool:
    if isinstance(programa_id, str):
        try:
            programa_id = uuid.UUID(programa_id)
        except ValueError:
            return False

    programa = get_programa(programa_id)
    if programa is None:
        return False

    upload_root = current_app.config["UPLOAD_FOLDER"]
    for sesion in list(programa.sesiones):
        sesion_dir = upload_root / str(sesion.id)
        if sesion_dir.exists():
            shutil.rmtree(sesion_dir)

    db.session.delete(programa)
    db.session.commit()
    return True
