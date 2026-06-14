from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class Gimnasio(db.Model):
    __tablename__ = "gimnasios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    direccion: Mapped[Optional[str]] = mapped_column(Text)
    ciudad: Mapped[Optional[str]] = mapped_column(String(100))
    telefono: Mapped[Optional[str]] = mapped_column(String(30))
    email_contacto: Mapped[Optional[str]] = mapped_column(String(255))
    zona_horaria: Mapped[str] = mapped_column(
        String(50), nullable=False, default="America/Santiago"
    )
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    profesores: Mapped[list["Profesor"]] = relationship(back_populates="gimnasio")
    tipos_clase: Mapped[list["TipoClase"]] = relationship(back_populates="gimnasio")
    clases: Mapped[list["Clase"]] = relationship(back_populates="gimnasio")
    programas: Mapped[list["ProgramaClase"]] = relationship(back_populates="gimnasio")


class Profesor(db.Model):
    __tablename__ = "profesores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    gimnasio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gimnasios.id"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    apellido: Mapped[Optional[str]] = mapped_column(String(150))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    telefono: Mapped[Optional[str]] = mapped_column(String(30))
    especialidades: Mapped[Optional[str]] = mapped_column(Text)
    bio: Mapped[Optional[str]] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    gimnasio: Mapped["Gimnasio"] = relationship(back_populates="profesores")
    clases: Mapped[list["Clase"]] = relationship(back_populates="profesor")
    programas: Mapped[list["ProgramaClase"]] = relationship(back_populates="profesor")

    @property
    def nombre_completo(self) -> str:
        if self.apellido:
            return f"{self.nombre} {self.apellido}"
        return self.nombre


class TipoClase(db.Model):
    __tablename__ = "tipos_clase"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    gimnasio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gimnasios.id"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    duracion_tipica_min: Mapped[Optional[int]] = mapped_column(Integer)
    capacidad_maxima: Mapped[Optional[int]] = mapped_column(Integer)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    gimnasio: Mapped["Gimnasio"] = relationship(back_populates="tipos_clase")
    clases: Mapped[list["Clase"]] = relationship(back_populates="tipo_clase")
    programas: Mapped[list["ProgramaClase"]] = relationship(back_populates="tipo_clase")


class ProgramaClase(db.Model):
    """Clase recurrente (p. ej. Pilates martes 10:00). Agrupa sesiones semanales."""

    __tablename__ = "programas_clase"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    gimnasio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gimnasios.id"), nullable=False
    )
    profesor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profesores.id"), nullable=False
    )
    tipo_clase_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tipos_clase.id"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    sala: Mapped[Optional[str]] = mapped_column(String(100))
    nivel: Mapped[Optional[str]] = mapped_column(String(50))
    notas: Mapped[Optional[str]] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    gimnasio: Mapped["Gimnasio"] = relationship(back_populates="programas")
    profesor: Mapped["Profesor"] = relationship(back_populates="programas")
    tipo_clase: Mapped["TipoClase"] = relationship(back_populates="programas")
    sesiones: Mapped[list["Clase"]] = relationship(
        back_populates="programa", cascade="all, delete-orphan"
    )

    @property
    def sesiones_visibles(self) -> list["Clase"]:
        return [s for s in self.sesiones if s.status != "awaiting_upload"]

    @property
    def num_sesiones(self) -> int:
        return len(self.sesiones_visibles)

    @property
    def ultima_sesion(self) -> Optional["Clase"]:
        visibles = self.sesiones_visibles
        if not visibles:
            return None
        return max(visibles, key=lambda s: s.fecha_inicio)


class Clase(db.Model):
    __tablename__ = "clases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    gimnasio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gimnasios.id"), nullable=False
    )
    profesor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profesores.id"), nullable=False
    )
    tipo_clase_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tipos_clase.id"), nullable=False
    )
    programa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("programas_clase.id"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    fecha_inicio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    fecha_fin: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    sala: Mapped[Optional[str]] = mapped_column(String(100))
    nivel: Mapped[Optional[str]] = mapped_column(String(50))
    cupos_planificados: Mapped[Optional[int]] = mapped_column(Integer)
    notas: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pendiente_analisis"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    gimnasio: Mapped["Gimnasio"] = relationship(back_populates="clases")
    profesor: Mapped["Profesor"] = relationship(back_populates="clases")
    tipo_clase: Mapped["TipoClase"] = relationship(back_populates="clases")
    programa: Mapped["ProgramaClase"] = relationship(back_populates="sesiones")
    archivos: Mapped[list["ArchivoMedia"]] = relationship(
        back_populates="clase", cascade="all, delete-orphan"
    )
    analisis_jobs: Mapped[list["AnalisisJob"]] = relationship(
        back_populates="clase", cascade="all, delete-orphan"
    )
    metricas: Mapped[list["Metrica"]] = relationship(
        back_populates="clase", cascade="all, delete-orphan"
    )

    @property
    def tiene_video(self) -> bool:
        return any(a.tipo == "video" for a in self.archivos)

    @property
    def tiene_audio(self) -> bool:
        return any(a.tipo == "audio" for a in self.archivos)


class ArchivoMedia(db.Model):
    __tablename__ = "archivos_media"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    clase_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clases.id"), nullable=False
    )
    tipo: Mapped[str] = mapped_column(String(10), nullable=False)
    nombre_original: Mapped[str] = mapped_column(String(255), nullable=False)
    extension: Mapped[str] = mapped_column(String(10), nullable=False)
    ruta_local: Mapped[Optional[str]] = mapped_column(String(500))
    s3_bucket: Mapped[Optional[str]] = mapped_column(String(100))
    s3_key: Mapped[Optional[str]] = mapped_column(String(500))
    tamano_bytes: Mapped[Optional[int]] = mapped_column(BigInteger)
    duracion_segundos: Mapped[Optional[float]] = mapped_column(Numeric(12, 2))
    mime_type: Mapped[Optional[str]] = mapped_column(String(100))
    checksum: Mapped[Optional[str]] = mapped_column(String(64))
    subido_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    clase: Mapped["Clase"] = relationship(back_populates="archivos")


class AnalisisJob(db.Model):
    __tablename__ = "analisis_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    clase_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clases.id"), nullable=False
    )
    archivo_media_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("archivos_media.id")
    )
    proveedor: Mapped[str] = mapped_column(String(20), nullable=False, default="aws")
    servicio: Mapped[str] = mapped_column(String(50), nullable=False)
    job_id_externo: Mapped[Optional[str]] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    intentos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_mensaje: Mapped[Optional[str]] = mapped_column(Text)
    request_payload: Mapped[Optional[dict]] = mapped_column(JSONB)
    raw_response: Mapped[Optional[dict]] = mapped_column(JSONB)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    clase: Mapped["Clase"] = relationship(back_populates="analisis_jobs")
    archivo: Mapped[Optional["ArchivoMedia"]] = relationship()
    metricas: Mapped[list["Metrica"]] = relationship(back_populates="analisis_job")


class Metrica(db.Model):
    __tablename__ = "metricas"
    __table_args__ = (UniqueConstraint("clase_id", "clave", name="uq_metrica_clase_clave"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    clase_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clases.id"), nullable=False
    )
    analisis_job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analisis_jobs.id")
    )
    clave: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    valor_numerico: Mapped[Optional[float]] = mapped_column(Numeric(12, 4))
    valor_texto: Mapped[Optional[str]] = mapped_column(Text)
    unidad: Mapped[Optional[str]] = mapped_column(String(30))
    confianza: Mapped[Optional[float]] = mapped_column(Numeric(5, 4))
    detalle: Mapped[Optional[dict]] = mapped_column(JSONB)
    calculado_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    clase: Mapped["Clase"] = relationship(back_populates="metricas")
    analisis_job: Mapped[Optional["AnalisisJob"]] = relationship(back_populates="metricas")
