"""Clientes de bajo nivel para servicios AWS (S3, Rekognition, Transcribe, etc.)."""

from app.services.aws.s3_client import (
    check_object_exists,
    generate_presigned_upload_url,
    generate_presigned_url,
    get_s3_uri,
)
from app.services.aws.rekognition_client import (
    get_face_detection_result,
    get_person_tracking_result,
    start_face_detection,
    start_person_tracking,
)
from app.services.aws.transcribe_client import get_transcription_result, start_transcription
from app.services.aws.comprehend_client import analyze_sentiment

__all__ = [
    "check_object_exists",
    "generate_presigned_upload_url",
    "generate_presigned_url",
    "get_s3_uri",
    "start_person_tracking",
    "start_face_detection",
    "get_person_tracking_result",
    "get_face_detection_result",
    "start_transcription",
    "get_transcription_result",
    "analyze_sentiment",
]
