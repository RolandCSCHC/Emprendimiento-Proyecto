"""Clientes de bajo nivel para servicios AWS (S3, Rekognition, Transcribe, etc.)."""

from app.services.aws.s3_client import check_object_exists, generate_presigned_upload_url, get_s3_uri
from app.services.aws.rekognition_client import get_video_job_result, start_video_analysis
from app.services.aws.transcribe_client import get_transcription_result, start_transcription
from app.services.aws.comprehend_client import analyze_text_sentiment

__all__ = [
    "generate_presigned_upload_url",
    "check_object_exists",
    "get_s3_uri",
    "start_video_analysis",
    "get_video_job_result",
    "start_transcription",
    "get_transcription_result",
    "analyze_text_sentiment",
]
