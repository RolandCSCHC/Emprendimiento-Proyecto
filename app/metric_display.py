"""Formateo de valores de métricas para la UI."""

from __future__ import annotations

from typing import Any, Optional


def format_metric_value(clave: str, valor_numerico: Any, unidad: Optional[str] = None) -> str:
    """
    Devuelve el texto a mostrar para una métrica numérica completada.

    - asistencia: entero + «personas»
    - permanencia, tiempo_hablando_vs_demostrando: dos decimales + «%»
    - claridad_instrucciones, satisfaccion_alumno: dos decimales + «score»
    """
    if valor_numerico is None:
        return ""

    value = float(valor_numerico)

    if clave == "asistencia":
        return f"{int(round(value))} personas"
    if clave in ("permanencia", "tiempo_hablando_vs_demostrando"):
        return f"{value:.2f}%"
    if clave in ("claridad_instrucciones", "satisfaccion_alumno"):
        return f"{value:.2f} score"

    if unidad:
        return f"{value} {unidad}"
    return f"{value}"
