# Gymsight

Software integral que analiza audio y video de clases grupales para obtener datos reales sobre asistencia, participación y dinámica de la clase, entregando métricas y recomendaciones sin interrumpir a los alumnos ni depender de encuestas tradicionales.

## Requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (incluye Docker Compose)

## Inicio rápido

Desde la carpeta del proyecto:

```bash
cp .env.example .env
docker compose up --build
```

La primera vez puede tardar unos minutos (descarga de imágenes y construcción).

Cuando veas que el servicio `web` está en marcha, abre en el navegador:

**http://localhost:5001**

Para detener la aplicación: `Ctrl+C` y luego:

```bash
docker compose down
```

Para volver a levantarla sin reconstruir:

```bash
docker compose up
```

## Uso de la aplicación

1. Ve a **Subir clase** y completa gimnasio, profesor, tipo, nombre, fecha y archivos (video y/o audio).
2. Tras crear la clase, verás el detalle con las métricas en estado pendiente.
3. En **Dashboard** aparecen todas las clases registradas.

Al arrancar, la app crea automáticamente las tablas y datos de demostración (1 gimnasio, 3 profesores, 4 tipos de clase).

## Comandos útiles

| Comando | Descripción |
|---------|-------------|
| `docker compose up --build` | Construye y levanta app + base de datos |
| `docker compose up -d` | Levanta en segundo plano |
| `docker compose down` | Detiene y elimina contenedores |
| `docker compose down -v` | Detiene y **borra** datos (BD y uploads) |
| `docker compose logs -f web` | Ver logs de la aplicación |
| `docker compose ps` | Estado de los contenedores |

## Conectar DBeaver (u otro cliente SQL)

Con los contenedores en marcha (`docker compose up`):

| Campo | Valor |
|-------|--------|
| Host | `localhost` |
| Port | `5433` |
| Database | `gymsight` |
| Username | `gymsight` |
| Password | `gymsight` |

> Usa el puerto **5433** (no 5432). La app dentro de Docker habla con Postgres por la red interna; desde tu Mac usas el puerto publicado **5433**.

## Variables de entorno

Copia `.env.example` a `.env` antes del primer `docker compose up`:

| Variable | Descripción |
|----------|-------------|
| `SECRET_KEY` | Clave secreta de Flask (cámbiala en producción) |
| `MAX_UPLOAD_MB` | Tamaño máximo de subida por archivo (default: 500) |

`DATABASE_URL` lo define Docker Compose para el contenedor `web`; no hace falta editarlo para uso local.

## Arquitectura Docker

```
┌─────────────┐     ┌──────────────┐
│   Navegador │────▶│ web :5001    │  Flask + Gunicorn
└─────────────┘     └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  db :5432    │  PostgreSQL
                    └──────────────┘
         (expuesto en localhost:5433)
```

## Modelo de datos

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
app/                 # Código Flask
docker/              # entrypoint del contenedor
migrations/          # Migraciones de base de datos
docker-compose.yml
Dockerfile
```
