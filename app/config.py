import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", 500))
    MAX_CONTENT_LENGTH = MAX_UPLOAD_MB * 1024 * 1024

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql://gymsight:gymsight@db:5432/gymsight",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = BASE_DIR / "uploads"

    ALLOWED_VIDEO_EXTENSIONS = {"mp4", "webm", "mov"}
    ALLOWED_AUDIO_EXTENSIONS = {"mp3", "wav", "m4a", "ogg"}

    METRIC_KEYS = [
        "asistencia",
        "permanencia",
        "claridad_instrucciones",
        "tiempo_hablando_vs_demostrando",
        "satisfaccion_alumno",
    ]

    METRIC_LABELS = {
        "asistencia": "Asistencia",
        "permanencia": "Permanencia",
        "claridad_instrucciones": "Claridad de Instrucciones",
        "tiempo_hablando_vs_demostrando": "Tiempo Hablando vs. Demostrando",
        "satisfaccion_alumno": "Satisfacción del Alumno",
    }

    # AWS (fase futura — ver README)
    AWS_ENABLED = os.environ.get("AWS_ENABLED", "false").lower() == "true"
    AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
    AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
    S3_BUCKET = os.environ.get("S3_BUCKET", "")
    SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN")
    TRANSCRIBE_OUTPUT_BUCKET = os.environ.get("TRANSCRIBE_OUTPUT_BUCKET")
    # Idioma de Transcribe. "auto" detecta automáticamente entre LANGUAGE_OPTIONS;
    # o pon un código fijo (es-ES, en-US, ...) para forzarlo.
    TRANSCRIBE_LANGUAGE_CODE = os.environ.get("TRANSCRIBE_LANGUAGE_CODE", "auto")
    TRANSCRIBE_LANGUAGE_OPTIONS = os.environ.get(
        "TRANSCRIBE_LANGUAGE_OPTIONS", "es-ES,en-US"
    ).split(",")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    AWS_ENABLED = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "TEST_DATABASE_URL", "sqlite+pysqlite:///:memory:"
    )


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
