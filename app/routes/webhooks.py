"""
Webhook para notificaciones SNS de AWS (fin de jobs Rekognition/Transcribe).

Valida la firma del mensaje SNS antes de procesarlo, confirma suscripciones y,
ante una Notification, dispara ``process_completed_job`` para el job indicado.
"""

from __future__ import annotations

import base64
import json
from typing import Any
from urllib.parse import urlparse

import requests
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.x509 import load_pem_x509_certificate
from flask import Blueprint, current_app, jsonify, request

from app.models import AnalisisJob
from app.services.analysis_service import process_completed_job

webhooks_bp = Blueprint("webhooks", __name__, url_prefix="/webhooks")

# Campos firmados por SNS (en orden) según el tipo de mensaje.
_SIGNING_KEYS = {
    "Notification": ["Message", "MessageId", "Subject", "Timestamp", "TopicArn", "Type"],
    "SubscriptionConfirmation": [
        "Message", "MessageId", "SubscribeURL", "Timestamp", "Token", "TopicArn", "Type",
    ],
    "UnsubscribeConfirmation": [
        "Message", "MessageId", "SubscribeURL", "Timestamp", "Token", "TopicArn", "Type",
    ],
}


@webhooks_bp.route("/aws/sns", methods=["POST"])
def aws_sns_webhook():
    try:
        message = json.loads(request.get_data(as_text=True))
    except (ValueError, TypeError):
        return jsonify({"error": "Cuerpo JSON inválido"}), 400

    if not _verify_sns_signature(message):
        return jsonify({"error": "Firma SNS inválida"}), 403

    msg_type = message.get("Type")
    if msg_type == "SubscriptionConfirmation":
        _confirm_subscription(message)
        return jsonify({"status": "subscription confirmed"}), 200
    if msg_type == "Notification":
        return _handle_notification(message)
    return jsonify({"status": "ignored", "type": msg_type}), 200


def _handle_notification(message: dict[str, Any]):
    job_id = _extract_job_id(message)
    if not job_id:
        return jsonify({"error": "No se encontró job_id en la notificación"}), 400

    job = AnalisisJob.query.filter_by(job_id_externo=job_id).first()
    if job is None:
        return jsonify({"error": f"Job no encontrado: {job_id}"}), 400

    process_completed_job(str(job.id))
    return jsonify({"status": "processed", "job_id": job_id}), 200


def _extract_job_id(message: dict[str, Any]) -> str | None:
    """Extrae el JobId externo del cuerpo de la notificación (Rekognition/Transcribe)."""
    raw = message.get("Message")
    if isinstance(raw, str):
        try:
            inner = json.loads(raw)
        except ValueError:
            inner = {}
    elif isinstance(raw, dict):
        inner = raw
    else:
        inner = {}
    return inner.get("JobId") or message.get("JobId")


def _confirm_subscription(message: dict[str, Any]) -> None:
    subscribe_url = message.get("SubscribeURL")
    if subscribe_url:
        requests.get(subscribe_url, timeout=10)


def _canonical_message(message: dict[str, Any]) -> bytes:
    keys = _SIGNING_KEYS.get(message.get("Type"), [])
    lines: list[str] = []
    for key in keys:
        if key in message:
            lines.append(key)
            lines.append(message[key])
    return "".join(f"{value}\n" for value in lines).encode("utf-8")


def _verify_sns_signature(message: dict[str, Any]) -> bool:
    """Verifica la firma RSA del mensaje SNS con el certificado X.509 de AWS."""
    cert_url = message.get("SigningCertURL")
    signature_b64 = message.get("Signature")
    if not cert_url or not signature_b64:
        return False

    parsed = urlparse(cert_url)
    if parsed.scheme != "https" or not parsed.netloc.endswith(".amazonaws.com"):
        return False  # evita SSRF: solo certificados de AWS

    try:
        cert_pem = requests.get(cert_url, timeout=10).content
        public_key = load_pem_x509_certificate(cert_pem).public_key()
        signature = base64.b64decode(signature_b64)
        algorithm = hashes.SHA1() if message.get("SignatureVersion") == "1" else hashes.SHA256()
        public_key.verify(signature, _canonical_message(message), padding.PKCS1v15(), algorithm)
        return True
    except Exception:  # noqa: BLE001 - cualquier fallo invalida la firma
        current_app.logger.warning("Firma SNS no verificada")
        return False
