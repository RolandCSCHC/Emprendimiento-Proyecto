"""Generación de recomendaciones IA para profesores a partir de su historial.

Agrega las métricas de todas las sesiones completadas del profesor, calcula
estadísticas resumidas y tendencias, construye un prompt y lo envía a Bedrock
(Amazon Nova) para producir 3-5 recomendaciones accionables en español.

Las recomendaciones no se persisten: se generan bajo demanda.
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field

from flask import current_app

from app.extensions import db
from app.models import Clase, Metrica
from app.services.aws.bedrock_client import (
    BedrockInvocationError,
    ConfigurationError,
    invoke_model,
)

logger = logging.getLogger(__name__)

# Sesiones que cuentan como "analizadas" para agregar métricas.
COMPLETED_STATUSES = ("completada", "completada_parcial")
# Mínimo de sesiones para que las recomendaciones tengan sentido estadístico.
MIN_SESSIONS = 2
# Tolerancia relativa para clasificar una tendencia como "estable".
TREND_TOLERANCE = 0.02

# Contexto por métrica: qué mide (desde video/audio, sin encuestas), su unidad y
# las palancas concretas que el profesor controla en clase para moverla. Se inyecta
# en el prompt para que las recomendaciones sean específicas y aplicables.
METRIC_CONTEXT: dict[str, dict[str, str]] = {
    "asistencia": {
        "unidad": "personas",
        "mide": "cantidad de alumnos detectados en el video de la clase",
        "palancas": (
            "puntualidad al iniciar, variar la rutina entre sesiones, calentamiento "
            "atractivo en los primeros minutos, nombrar el plan de la clase al empezar"
        ),
    },
    "permanencia": {
        "unidad": "%",
        "mide": "porcentaje de alumnos que siguen presentes al final respecto al inicio",
        "palancas": (
            "mantener intensidad y energía en el tramo final, evitar tiempos muertos "
            "y transiciones lentas, reservar un ejercicio motivador para el cierre, "
            "estructurar la sesión para que lo mejor no quede solo al principio"
        ),
    },
    "claridad_instrucciones": {
        "unidad": "score 0-100",
        "mide": "claridad del habla del profesor (ritmo, largo de frases y pausas) en el audio",
        "palancas": (
            "instrucciones cortas y concretas, conteos claros (uno, dos, tres), "
            "hacer pausas entre indicaciones, bajar el ritmo de habla, una indicación "
            "por movimiento en vez de varias juntas"
        ),
    },
    "tiempo_hablando_vs_demostrando": {
        "unidad": "% del tiempo hablando",
        "mide": "proporción del tiempo que el profesor habla frente a demostrar/ejecutar (audio)",
        "palancas": (
            "demostrar el movimiento en vez de describirlo, ejecutar junto a los alumnos, "
            "usar señales corporales y conteo en lugar de explicaciones largas, "
            "hablar mientras se mueve y no de pie explicando"
        ),
    },
    "satisfaccion_alumno": {
        "unidad": "score 0-100",
        "mide": "proxy de satisfacción a partir de expresiones faciales (video) y tono del audio",
        "palancas": (
            "refuerzo positivo durante la clase, energía y entusiasmo en la voz, "
            "música acorde a la intensidad, reconocer el esfuerzo del grupo, "
            "cierres motivadores"
        ),
    },
}


@dataclass
class MetricSummary:
    """Resumen estadístico de una métrica a lo largo de las sesiones."""

    metric_key: str
    average: float
    minimum: float
    maximum: float
    trend: str  # "mejorando" | "estable" | "empeorando"
    session_count: int


@dataclass
class RecommendationResult:
    """Resultado de la generación de recomendaciones."""

    recommendations: list[str] = field(default_factory=list)
    status: str = "success"  # "success" | "insufficient_data" | "error"
    message: str | None = None


def _compute_trend(values: list[float]) -> str:
    """Clasifica la tendencia comparando la primera mitad con la segunda."""
    if len(values) < 2:
        return "estable"
    mid = len(values) // 2
    first = values[:mid]
    second = values[mid:]
    first_mean = sum(first) / len(first)
    second_mean = sum(second) / len(second)
    base = abs(first_mean) if first_mean else 1.0
    diff = second_mean - first_mean
    if diff > TREND_TOLERANCE * base:
        return "mejorando"
    if diff < -TREND_TOLERANCE * base:
        return "empeorando"
    return "estable"


def aggregate_professor_metrics(
    profesor_id: str | uuid.UUID,
) -> list[MetricSummary] | None:
    """
    Recopila y agrega métricas de todas las sesiones completadas del profesor.

    Returns:
        Lista de ``MetricSummary`` (una por métrica con datos), o ``None`` si el
        profesor tiene menos de ``MIN_SESSIONS`` sesiones completadas.
    """
    try:
        parsed_id = profesor_id if isinstance(profesor_id, uuid.UUID) else uuid.UUID(
            str(profesor_id)
        )
    except ValueError:
        return None

    metric_keys = current_app.config["METRIC_KEYS"]

    sesiones = (
        Clase.query.options(db.joinedload(Clase.metricas))
        .filter(
            Clase.profesor_id == parsed_id,
            Clase.status.in_(COMPLETED_STATUSES),
        )
        .order_by(Clase.fecha_inicio.asc())
        .all()
    )

    if len(sesiones) < MIN_SESSIONS:
        return None

    # Valores numéricos por métrica, en orden cronológico de sesión.
    values_by_key: dict[str, list[float]] = {key: [] for key in metric_keys}
    for sesion in sesiones:
        metricas_by_key = {m.clave: m for m in sesion.metricas}
        for key in metric_keys:
            metrica: Metrica | None = metricas_by_key.get(key)
            if (
                metrica
                and metrica.status == "completed"
                and metrica.valor_numerico is not None
            ):
                values_by_key[key].append(float(metrica.valor_numerico))

    summaries: list[MetricSummary] = []
    for key in metric_keys:
        values = values_by_key[key]
        if not values:
            continue
        summaries.append(
            MetricSummary(
                metric_key=key,
                average=sum(values) / len(values),
                minimum=min(values),
                maximum=max(values),
                trend=_compute_trend(values),
                session_count=len(values),
            )
        )

    return summaries


def build_prompt(summaries: list[MetricSummary], profesor_nombre: str) -> str:
    """Construye el prompt para Bedrock con las estadísticas del profesor."""
    metric_labels = current_app.config["METRIC_LABELS"]
    session_count = max((s.session_count for s in summaries), default=0)

    lineas = []
    for s in summaries:
        label = metric_labels.get(s.metric_key, s.metric_key)
        ctx = METRIC_CONTEXT.get(s.metric_key, {})
        unidad = ctx.get("unidad", "")
        mide = ctx.get("mide", "")
        palancas = ctx.get("palancas", "")
        lineas.append(
            f"- {label} ({mide}):\n"
            f"    promedio {s.average:.1f} {unidad}, mín {s.minimum:.1f}, "
            f"máx {s.maximum:.1f}, tendencia: {s.trend}\n"
            f"    palancas que el profesor controla: {palancas}"
        )
    datos = "\n".join(lineas)

    return (
        "Eres un coach de profesores de fitness y yoga. Tu trabajo es darle al "
        f"profesor {profesor_nombre} acciones concretas que pueda aplicar EN SU "
        "PRÓXIMA CLASE para que sus métricas y sus clases mejoren.\n\n"
        "Contexto del producto: estas métricas se obtienen automáticamente "
        "analizando el VIDEO y el AUDIO de las clases. El objetivo es que el "
        "profesor mejore SIN tener que hacer encuestas ni preguntarles nada a los "
        "alumnos: los datos ya le dicen qué pasa.\n\n"
        f"Datos del profesor ({session_count} sesiones analizadas):\n\n"
        f"{datos}\n\n"
        "Reglas para tus recomendaciones:\n"
        "- PROHIBIDO recomendar encuestas, formularios, cuestionarios, "
        "buzones de sugerencias o pedirles feedback/opinión a los alumnos. "
        "Eso va en contra del producto y hace inútil la recomendación.\n"
        "- Cada recomendación debe ser una ACCIÓN que el profesor ejecuta él mismo "
        "(una técnica de enseñanza, una forma de estructurar la sesión, cómo habla, "
        "cómo demuestra, cómo maneja la energía y el ritmo). Nada que dependa de "
        "preguntarle a los alumnos.\n"
        "- Sé específico y práctico: di QUÉ hacer y CÓMO, no generalidades. "
        "Usa las 'palancas' de cada métrica como guía.\n"
        "- Prioriza las métricas más bajas o con tendencia 'empeorando'. "
        "Menciona el dato concreto que justifica cada consejo.\n"
        "- Responde SOLO en español.\n"
        "- Genera entre 3 y 5 recomendaciones, numeradas (1., 2., 3., ...).\n"
        "- Empieza cada una con un título corto seguido de dos puntos y luego la "
        "acción concreta (ej: 'Demostrar más y hablar menos: ...').\n"
        "- Escribe en texto plano, SIN Markdown ni asteriscos.\n"
        "- No incluyas introducción ni cierre, solo la lista numerada."
    )


_NUMBER_PREFIX = re.compile(r"^\s*(?:\d+[\.\)]|[-*•])\s+")
# Marcadores Markdown que el modelo a veces incluye pese a pedir texto plano.
_MD_BOLD = re.compile(r"\*\*(.+?)\*\*")
_MD_LEFTOVER = re.compile(r"[*_`#]+")


def _clean_markdown(text: str) -> str:
    """Quita formato Markdown (negritas, etc.) dejando texto plano legible."""
    text = _MD_BOLD.sub(r"\1", text)  # **negrita** -> negrita
    text = _MD_LEFTOVER.sub("", text)  # restos sueltos de *, _, `, #
    return re.sub(r"\s{2,}", " ", text).strip()


def parse_recommendations(model_response: str) -> list[str]:
    """Parsea la respuesta del modelo en una lista de recomendaciones."""
    if not model_response:
        return []

    items: list[str] = []
    for raw_line in model_response.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if _NUMBER_PREFIX.match(line):
            items.append(_NUMBER_PREFIX.sub("", line).strip())
        elif items:
            # Continuación de la recomendación anterior (texto que sigue en
            # la línea de abajo sin numeración).
            items[-1] = f"{items[-1]} {line}".strip()

    # Fallback: si no se detectó numeración, usar líneas no vacías.
    if not items:
        items = [
            line.strip() for line in model_response.splitlines() if line.strip()
        ]

    cleaned = (_clean_markdown(item) for item in items)
    return [item for item in cleaned if item]


def generate_recommendations(profesor_id: str | uuid.UUID) -> RecommendationResult:
    """Flujo completo: agrega datos → construye prompt → invoca modelo → parsea."""
    from app.models import Profesor

    summaries = aggregate_professor_metrics(profesor_id)
    if summaries is None or not summaries:
        return RecommendationResult(
            status="insufficient_data",
            message=(
                "Se necesitan al menos 2 sesiones analizadas para generar "
                "recomendaciones."
            ),
        )

    profesor = db.session.get(Profesor, profesor_id) if not isinstance(
        profesor_id, str
    ) else Profesor.query.filter_by(id=profesor_id).first()
    profesor_nombre = profesor.nombre_completo if profesor else "el profesor"

    prompt = build_prompt(summaries, profesor_nombre)

    try:
        respuesta = invoke_model(prompt)
    except (ConfigurationError, BedrockInvocationError) as exc:
        logger.error("No se pudieron generar recomendaciones: %s", exc)
        return RecommendationResult(
            status="error",
            message="No se pudieron generar recomendaciones en este momento.",
        )

    if not respuesta:
        # AWS deshabilitado u otra degradación elegante.
        return RecommendationResult(
            status="error",
            message="El servicio de recomendaciones no está disponible.",
        )

    recomendaciones = parse_recommendations(respuesta)
    logger.info(
        "Recomendaciones generadas para profesor %s: %d",
        profesor_id,
        len(recomendaciones),
    )
    return RecommendationResult(recommendations=recomendaciones, status="success")
