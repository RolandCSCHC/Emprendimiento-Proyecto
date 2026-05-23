"""Clientes de bajo nivel para servicios AWS (S3, Rekognition, Transcribe, etc.)."""

from app.services.aws.s3_client import upload_archivo_to_s3
from app.services.aws.rekognition_client import get_video_job_result, start_video_analysis
from app.services.aws.transcribe_client import get_transcription_result, start_transcription
from app.services.aws.comprehend_client import analyze_text_sentiment

__all__ = [
    "upload_archivo_to_s3",
    "start_video_analysis",
    "get_video_job_result",
    "start_transcription",
    "get_transcription_result",
    "analyze_text_sentiment",
]
