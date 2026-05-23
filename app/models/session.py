from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class MetricInfo:
    status: str = "pending"
    value: Any = None

    def to_dict(self) -> dict:
        data = {"status": self.status}
        if self.value is not None:
            data["value"] = self.value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "MetricInfo":
        return cls(status=data.get("status", "pending"), value=data.get("value"))


@dataclass
class ClassSession:
    id: str
    nombre: str
    fecha: str
    status: str = "pending"
    video_filename: str | None = None
    audio_filename: str | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metricas: dict[str, MetricInfo] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nombre": self.nombre,
            "fecha": self.fecha,
            "status": self.status,
            "video_filename": self.video_filename,
            "audio_filename": self.audio_filename,
            "created_at": self.created_at,
            "metricas": {key: metric.to_dict() for key, metric in self.metricas.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ClassSession":
        metricas = {
            key: MetricInfo.from_dict(value)
            for key, value in data.get("metricas", {}).items()
        }
        return cls(
            id=data["id"],
            nombre=data["nombre"],
            fecha=data["fecha"],
            status=data.get("status", "pending"),
            video_filename=data.get("video_filename"),
            audio_filename=data.get("audio_filename"),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            metricas=metricas,
        )
