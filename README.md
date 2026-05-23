# Gymsight

Software integral que analiza audio y video de clases grupales para obtener datos reales sobre asistencia, participación y dinámica de la clase, entregando métricas y recomendaciones sin interrumpir a los alumnos ni depender de encuestas tradicionales.

## Fase actual — Flask + PostgreSQL

- Subida de video y/o audio por clase
- Datos de gimnasio, profesor y tipo de clase (yoga, pilates, etc.)
- Dashboard con listado y detalle
- 5 métricas en estado pendiente hasta integrar AWS
- Persistencia en PostgreSQL

Próximas fases: Docker completo, integración AWS.

## Requisitos

- Python 3.9 o superior
- PostgreSQL 16 (o Docker)

## Base de datos con Docker

```bash
docker compose up -d
```

Esto levanta PostgreSQL en `localhost:5433` con usuario/contraseña/base: `gymsight`.

Asegúrate de que tu `.env` incluya:

```
DATABASE_URL=postgresql://gymsight:gymsight@localhost:5433/gymsight
```

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate   # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

## Inicializar la base de datos

Opción A — sin migraciones (rápido para desarrollo):

```bash
flask init-db
```

Opción B — con Flask-Migrate:

```bash
flask db init          # solo la primera vez
flask db migrate -m "Initial schema"
flask db upgrade
flask seed
```

## Ejecución

```bash
flask run
```

Abre [http://127.0.0.1:5000](http://127.0.0.1:5000).

## Uso

1. Ve a **Subir clase** y completa gimnasio, profesor, tipo, nombre, fecha y archivos.
2. Tras crear la clase, verás el detalle con métricas pendientes.
3. En **Dashboard** aparecen todas las clases registradas.

## Modelo de datos (7 tablas)

| Tabla | Descripción |
|-------|-------------|
| `gimnasios` | Sede / negocio |
| `profesores` | Instructores |
| `tipos_clase` | Yoga, Pilates, Spinning, etc. |
| `clases` | Instancia concreta de una clase |
| `archivos_media` | Videos y audios subidos |
| `analisis_jobs` | Jobs de análisis AWS (pendientes) |
| `metricas` | Las 5 métricas del dashboard |

## Métricas

- Asistencia
- Permanencia
- Claridad de Instrucciones
- Tiempo Hablando vs. Demostrando
- Satisfacción del Alumno

## Estructura del proyecto

```
app/              # Aplicación Flask
migrations/       # Migraciones Alembic (tras flask db init)
uploads/          # Archivos de media (gitignored)
docker-compose.yml
```
