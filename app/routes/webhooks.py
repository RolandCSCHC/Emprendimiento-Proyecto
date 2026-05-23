"""
Webhooks para notificaciones asíncronas de AWS (SNS).

Rekognition y Transcribe pueden publicar en un topic SNS cuando un job termina.
Este endpoint recibiría esa notificación y dispararía ``process_completed_job``.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request

webhooks_bp = Blueprint("webhooks", __name__, url_prefix="/webhooks")


@webhooks_bp.route("/aws/sns", methods=["POST"])
def aws_sns_webhook():
    """
    Recibe mensajes SNS de AWS.

    A implementar:
    1. Validar firma del mensaje SNS (seguridad).
    2. Si es SubscriptionConfirmation, confirmar suscripción.
    3. Si es Notification, parsear el body y extraer job_id / clase_id.
    4. Llamar ``analysis_service.process_completed_job(analisis_job_id)``.

    Mientras no esté implementado, responde 501.
    """
    return jsonify(
        {
            "error": "Webhook AWS no implementado",
            "message": "Ver README — Fase AWS",
        }
    ), 501
