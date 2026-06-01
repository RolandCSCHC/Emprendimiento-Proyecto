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

Al arrancar, la app crea automáticamente las tablas y datos de demostración (1 gimnasio, 3 profesores, 4 tipos de clase y 4 clases de ejemplo enlazadas a videos en S3).

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

## Variables de entorno

Copia `.env.example` a `.env` antes del primer `docker compose up`:

| Variable | Descripción |
|----------|-------------|
| `SECRET_KEY` | Clave secreta de Flask (cámbiala en producción) |
| `MAX_UPLOAD_MB` | Tamaño máximo de subida por archivo (default: 800) |

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
| `analisis_jobs` | Jobs de análisis AWS (Rekognition/Transcribe) |
| `metricas` | Las 5 métricas del dashboard |

## Métricas

- Asistencia
- Permanencia
- Claridad de Instrucciones
- Tiempo Hablando vs. Demostrando
- Satisfacción del Alumno

## Estructura del proyecto

```
app/
├── routes/              # Pantallas y webhooks
├── services/
│   ├── aws/             # Clientes S3, Rekognition, Transcribe, Comprehend
│   ├── analysis/        # Pipeline, poller, extractores de métricas
│   ├── analysis_service.py   # Punto de entrada: enqueue_analysis()
│   ├── class_service.py
│   └── upload_service.py
docker/
migrations/
docker-compose.yml
Dockerfile
```

---

## Fase AWS — análisis en la nube (implementada ✅)

El pipeline está **implementado y probado contra AWS real**. Procesa los videos de las
clases (almacenados en S3) y genera las 5 métricas del dashboard automáticamente.

> 📚 Documentación detallada en `docs/`:
> - **`PRESENTACION-AWS.md`** — cómo funciona + guion de demo.
> - **`AVANCES-AWS.md`** — bitácora técnica de la implementación.
> - **`DEPLOY.md`** — qué configurar para producción (rol IAM, env vars, etc.).

### Cómo se activa

En `.env`: `AWS_ENABLED=true` + credenciales (o rol IAM) + `S3_BUCKET` + `AWS_REGION`.
Con `AWS_ENABLED=false` la app funciona normal sin tocar AWS (los archivos se guardan local).

### Flujo real

```text
1. Usuario sube clase  (o el video ya está en S3 por cámaras/grabaciones)
2. El servidor crea la clase (estado "awaiting_upload") y devuelve URLs PRE-FIRMADAS
3. El navegador sube el video DIRECTO a S3 (no pasa por el servidor)
4. Al terminar, /upload/<id>/complete verifica el objeto en S3 y dispara el análisis
5. pipeline pone la clase en "analizando" y lanza jobs: Rekognition FaceDetection + Transcribe
6. flask aws-poll-jobs  (o webhook SNS) consulta el estado en AWS
7. al terminar, metrics_extractor (+ Comprehend) calcula las 5 métricas
8. clase.status = completada  →  el dashboard muestra los valores reales
```

> La subida es **directa cliente → S3** (presigned `PUT`), así el archivo no pasa por
> Flask. Requiere **CORS** en el bucket permitiendo `PUT` desde el origen de la app
> (ver `ALLOWED_ORIGINS` y `docs/DEPLOY.md`).

### Módulos del pipeline

| Archivo | Responsabilidad |
|---------|-----------------|
| `app/services/analysis_service.py` | Punto de entrada: `enqueue_analysis`, `poll_pending_jobs` |
| `app/services/analysis/pipeline.py` | Valida S3 y lanza los jobs AWS por cada archivo |
| `app/services/analysis/job_poller.py` | Consulta jobs, guarda resultados y dispara métricas |
| `app/services/analysis/metrics_extractor.py` | Convierte respuestas de AWS → tabla `metricas` |
| `app/services/aws/s3_client.py` | Subir, verificar y firmar URLs de objetos en S3 |
| `app/services/aws/rekognition_client.py` | FaceDetection (emociones + conteo de caras) |
| `app/services/aws/transcribe_client.py` | Transcripción de audio (con timestamps) |
| `app/services/aws/comprehend_client.py` | Sentimiento del texto transcrito |
| `app/routes/webhooks.py` | `POST /webhooks/aws/sns` (con validación de firma) |

### Servicios AWS por métrica

| Métrica | Servicio AWS |
|---------|--------------|
| Asistencia | Rekognition FaceDetection (pico de caras por tercio del video)* |
| Permanencia | Rekognition FaceDetection (caras al final vs. inicio)* |
| Claridad de Instrucciones | Transcribe (palabras/min, frases, pausas)** |
| Tiempo Hablando vs. Demostrando | Transcribe (segmentos con voz vs. silencio)** |
| Satisfacción del Alumno | Rekognition FaceDetection (emociones) + Comprehend (sentimiento) |

> *AWS **descontinuó Rekognition People Pathing** (tracking de personas) el 31-oct-2025, que
> era la fuente original de asistencia/permanencia. Se reemplazó por conteo de caras de
> FaceDetection. Para producción, lo más preciso sería Label Detection ("Person") o
> YOLOv9 + ByteTrack en SageMaker (ver `DEPLOY.md`).
>
> **Transcribe **detecta el idioma automáticamente** (`TRANSCRIBE_LANGUAGE_CODE=auto`)
> entre los candidatos de `TRANSCRIBE_LANGUAGE_OPTIONS` (es-ES/en-US), así una clase en
> español se transcribe en español y una en inglés en inglés. Si el video no tiene voz
> (p. ej. solo música), estas dos métricas salen 0 (correcto).

### Tablas de BD que usarás

| Tabla / columna | Uso en AWS |
|-----------------|------------|
| `archivos_media.s3_bucket`, `s3_key` | Ruta del archivo en S3 |
| `analisis_jobs.job_id_externo` | ID del job en Rekognition/Transcribe |
| `analisis_jobs.raw_response` | JSON completo devuelto por AWS |
| `analisis_jobs.status` | pending → submitted → in_progress → completed / failed |
| `metricas.valor_numerico`, `detalle` | Resultado final para el dashboard |
| `clases.status` | pendiente_analisis → analizando → completada / error |

### Variables de entorno (ver `.env.example`)

| Variable | Descripción |
|----------|-------------|
| `AWS_ENABLED` | `true` activa el pipeline (default: `false`) |
| `AWS_REGION` | Región, ej. `us-west-2` |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | Credenciales IAM (en producción: **dejar vacías y usar rol IAM**) |
| `S3_BUCKET` | Bucket con los videos |
| `TRANSCRIBE_LANGUAGE_CODE` | `auto` detecta el idioma solo (default), o fija uno (`es-ES`, `en-US`, ...) |
| `TRANSCRIBE_LANGUAGE_OPTIONS` | Idiomas candidatos para la auto-detección (ej. `es-ES,en-US`) |
| `ALLOWED_ORIGINS` | Orígenes permitidos para la subida directa (ej. `http://localhost:5001`) |
| `PRESIGNED_URL_EXPIRES` | Expiración (s) de las URLs pre-firmadas (default 900) |
| `SNS_TOPIC_ARN` / `REKOGNITION_SNS_ROLE_ARN` | Opcionales, solo si usas webhook SNS |

### Comandos del pipeline

```bash
# Disparar el análisis de las clases pendientes (o de una sola por id)
docker compose exec web flask aws-analyze
docker compose exec web flask aws-analyze <clase_id>

# Consultar el estado de los jobs y calcular métricas al terminar
docker compose exec web flask aws-poll-jobs
```

### Detección de jobs terminados

Los jobs de Rekognition/Transcribe son asíncronos. Dos formas de cerrarlos:

- **Polling**: `flask aws-poll-jobs` (manual, o con cron / EventBridge en producción).
- **Webhook SNS**: `POST /webhooks/aws/sns` (menor latencia; requiere URL pública HTTPS).

No hace falta Celery ni colas: AWS procesa en la nube.

### Permisos AWS necesarios

El usuario o rol IAM necesita: `s3:GetObject`, `s3:PutObject`, `rekognition:*`
(o al menos FaceDetection), `transcribe:*` y `comprehend:DetectSentiment`.

Para todo lo de producción (rol IAM, RDS, secrets, etc.) ver **`docs/DEPLOY.md`**.
