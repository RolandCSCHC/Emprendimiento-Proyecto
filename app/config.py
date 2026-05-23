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


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
