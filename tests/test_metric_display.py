from app.metric_display import format_metric_value


def test_asistencia_entero():
    assert format_metric_value("asistencia", 16.0) == "16 personas"
    assert format_metric_value("asistencia", 15.9999) == "16 personas"


def test_porcentajes_dos_decimales():
    assert format_metric_value("permanencia", 100) == "100.00%"
    assert format_metric_value("tiempo_hablando_vs_demostrando", 73.4) == "73.40%"


def test_scores_dos_decimales():
    assert format_metric_value("claridad_instrucciones", 72) == "72.00 score"
    assert format_metric_value("satisfaccion_alumno", 60.1234) == "60.12 score"
