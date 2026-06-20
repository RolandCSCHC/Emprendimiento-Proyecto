"""Blueprint de endpoints API (JSON) para carga asíncrona desde el frontend."""

from __future__ import annotations

import logging
import uuid

from flask import Blueprint, jsonify

from app.models import Profesor
from app.services.recommendation_service import generate_recommendations

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/profesores/<profesor_id>/recomendaciones", methods=["GET"])
def get_recommendations(profesor_id: str):
    """GET /api/profesores/<profesor_id>/recomendaciones"""
    try:
        uuid.UUID(profesor_id)
    except ValueError:
        return jsonify({"error": "Profesor no encontrado"}), 404

    profesor = Profesor.query.filter_by(id=profesor_id).first()
    if profesor is None:
        return jsonify({"error": "Profesor no encontrado"}), 404

    try:
        result = generate_recommendations(profesor_id)
    except Exception:  # noqa: BLE001 — última red de seguridad
        logger.exception("Error inesperado generando recomendaciones")
        return (
            jsonify({"error": "No se pudieron generar recomendaciones en este momento"}),
            503,
        )

    if result.status == "error":
        return jsonify({"error": result.message}), 503

    return (
        jsonify(
            {
                "recommendations": result.recommendations,
                "status": result.status,
                "message": result.message,
            }
        ),
        200,
    )
