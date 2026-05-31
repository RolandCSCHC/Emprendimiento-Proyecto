"""Constantes compartidas del pipeline de análisis (servicios y estados)."""

from __future__ import annotations

# Valores de AnalisisJob.servicio. Se usan como llaves en combined_raw_data.
SERVICE_PERSON_TRACKING = "rekognition_person_tracking"
SERVICE_FACE_DETECTION = "rekognition_face_detection"
SERVICE_TRANSCRIBE = "transcribe"
SERVICE_VALIDACION = "validacion"  # marcador para fallos de validación S3 (no se pollea)

# Estados de AnalisisJob.status
JOB_PENDING = "pending"
JOB_SUBMITTED = "submitted"
JOB_IN_PROGRESS = "in_progress"
JOB_COMPLETED = "completed"
JOB_FAILED = "failed"

# Estados de Clase.status
CLASE_ANALIZANDO = "analizando"
CLASE_COMPLETADA = "completada"
CLASE_COMPLETADA_PARCIAL = "completada_parcial"
CLASE_ERROR = "error"

# Estados de Metrica.status
METRICA_PENDING = "pending"
METRICA_COMPLETED = "completed"
METRICA_FAILED = "failed"
