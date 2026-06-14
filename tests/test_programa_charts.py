"""Tests de series de métricas y gráficos en programa_detail."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models import Clase, Metrica
from app.services.programa_service import chart_point_count, get_programa_metric_series
from tests.factories import crear_clase, crear_programa


def _add_metrics(clase: Clase, valores: dict[str, float]) -> None:
    for clave, valor in valores.items():
        db.session.add(
            Metrica(
                clase_id=clase.id,
                clave=clave,
                status="completed",
                valor_numerico=valor,
            )
        )
    db.session.flush()


def _sesion_completada(
    programa,
    *,
    day: int,
    valores: dict[str, float],
) -> Clase:
    fecha = datetime(2026, 3, day, 10, 0, tzinfo=timezone.utc)
    clase = Clase(
        gimnasio_id=programa.gimnasio_id,
        profesor_id=programa.profesor_id,
        tipo_clase_id=programa.tipo_clase_id,
        programa_id=programa.id,
        nombre=f"{programa.nombre} — {fecha.strftime('%d/%m/%Y %H:%M')}",
        fecha_inicio=fecha,
        status="completada",
    )
    db.session.add(clase)
    db.session.flush()
    _add_metrics(clase, valores)
    return clase


def test_get_programa_metric_series_ordenadas_por_fecha(app, db_session):
    programa = crear_programa()
    _sesion_completada(programa, day=10, valores={"asistencia": 10, "permanencia": 70})
    _sesion_completada(programa, day=3, valores={"asistencia": 8, "permanencia": 65})
    _sesion_completada(programa, day=17, valores={"asistencia": 12, "permanencia": 80})
    db_session.commit()

    series = get_programa_metric_series(programa.id)

    fechas = [p["fecha"] for p in series["asistencia"]]
    assert fechas == ["03/03/2026", "10/03/2026", "17/03/2026"]
    assert [p["valor"] for p in series["asistencia"]] == [8.0, 10.0, 12.0]
    assert [p["valor"] for p in series["permanencia"]] == [65.0, 70.0, 80.0]
    assert len(series) == 5
    assert chart_point_count(series) == 3


def test_get_programa_metric_series_ignora_pendientes(app, db_session):
    programa = crear_programa()
    _sesion_completada(programa, day=3, valores={"asistencia": 8})
    pendiente = crear_clase(programa=programa, status="pendiente_analisis")
    db.session.add(
        Metrica(clase_id=pendiente.id, clave="asistencia", status="pending")
    )
    db_session.commit()

    series = get_programa_metric_series(programa.id)
    assert len(series["asistencia"]) == 1
    assert chart_point_count(series) == 1


def test_programa_detail_incluye_charts_section(app, db_session, client):
    programa = crear_programa()
    _sesion_completada(programa, day=3, valores={"asistencia": 8, "permanencia": 70})
    db_session.commit()

    response = client.get(f"/dashboard/programas/{programa.id}")
    assert response.status_code == 200
    html = response.data.decode()
    assert "charts-section" in html
    assert "Evolución del semestre" in html
    assert "programa-charts" in html
    assert "programa_charts.js" in html


def test_programa_detail_sin_datos_muestra_empty(app, db_session, client):
    programa = crear_programa(nombre="Sin analisis")
    db_session.commit()

    response = client.get(f"/dashboard/programas/{programa.id}")
    assert response.status_code == 200
    html = response.data.decode()
    assert "charts-section" in html
    assert "Aún no hay sesiones analizadas" in html
