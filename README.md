# Gymsight

Software integral que analiza audio y video de clases grupales para obtener datos reales sobre asistencia, participación y dinámica de la clase, entregando métricas y recomendaciones sin interrumpir a los alumnos ni depender de encuestas tradicionales.

## Fase 1 — Flask funcional

Esta versión incluye:

- Subida de video y/o audio por clase
- Dashboard con listado y detalle de clases
- Las 5 métricas definidas en estado **Pendiente de análisis**
- Persistencia local en `data/sessions.json` y archivos en `uploads/`

Próximas fases: PostgreSQL, Docker e integración con AWS.

## Requisitos

- Python 3.11 o superior

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate   # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

## Ejecución

```bash
flask run
```

O alternativamente:

```bash
python run.py
```

Abre [http://127.0.0.1:5000](http://127.0.0.1:5000) en el navegador.

## Uso

1. Ve a **Subir clase** y completa el formulario (nombre, fecha, video y/o audio).
2. Tras crear la clase, serás redirigido al detalle con las métricas en estado pendiente.
3. En **Dashboard** puedes ver todas las clases registradas.

## Métricas

- Asistencia
- Permanencia
- Claridad de Instrucciones
- Tiempo Hablando vs. Demostrando
- Satisfacción del Alumno

## Estructura del proyecto

```
app/           # Aplicación Flask
data/          # Metadatos de clases (gitignored)
uploads/       # Archivos de media (gitignored)
run.py         # Punto de entrada
```
