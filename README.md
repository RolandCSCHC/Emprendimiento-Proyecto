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
app/
├── routes/              # Pantallas y webhooks
├── services/
│   ├── aws/             # Clientes S3, Rekognition, Transcribe (esqueleto)
│   ├── analysis/        # Pipeline, poller, extractores de métricas (esqueleto)
│   ├── analysis_service.py   # Punto de entrada: enqueue_analysis()
│   ├── class_service.py
│   └── upload_service.py
docker/
migrations/
docker-compose.yml
Dockerfile
```

---

## Fase AWS — integración con análisis en la nube (pendiente)

La app ya guarda clases, archivos y jobs en PostgreSQL. La conexión con AWS **no está implementada**; solo existe un **esqueleto** de archivos con docstrings para guiar el desarrollo.

### Punto de entrada actual

Tras crear una clase (o reemplazar video/audio al editar), se llama a:

```text
app/services/analysis_service.py  →  enqueue_analysis(clase_id)
```

Hoy `enqueue_analysis` no hace nada (`pass`). Cuando actives AWS, descomenta la llamada a `start_analysis_for_clase` dentro de ese archivo.

### Flujo objetivo

```text
1. Usuario sube clase
2. Flask guarda archivos en disco + registros en BD (analisis_jobs = pending)
3. enqueue_analysis(clase_id)
4. pipeline: sube archivos a S3 → lanza Rekognition / Transcribe
5. Jobs AWS corren en segundo plano (minutos)
6. job_poller o webhook SNS recibe el resultado
7. metrics_extractor escribe las 5 métricas + clase.status = completada
8. Dashboard muestra valores reales
```

### Archivos del esqueleto

| Archivo | Responsabilidad |
|---------|-----------------|
| `app/services/analysis_service.py` | Orquestador: `enqueue_analysis`, `poll_pending_jobs` |
| `app/services/analysis/pipeline.py` | Subir a S3 y disparar jobs por cada archivo |
| `app/services/analysis/job_poller.py` | Consultar jobs pendientes y guardar `raw_response` |
| `app/services/analysis/metrics_extractor.py` | Convertir JSON de AWS → tabla `metricas` |
| `app/services/aws/s3_client.py` | Subida de media a S3 |
| `app/services/aws/rekognition_client.py` | Análisis de video (asistencia, permanencia, etc.) |
| `app/services/aws/transcribe_client.py` | Transcripción de audio (claridad, habla) |
| `app/services/aws/comprehend_client.py` | Sentimiento del texto (opcional) |
| `app/routes/webhooks.py` | `POST /webhooks/aws/sns` para notificaciones SNS |

### Servicios AWS por métrica

| Métrica | Servicio AWS sugerido |
|---------|------------------------|
| Asistencia | Rekognition Video (detección de personas) |
| Permanencia | Rekognition Video (tracking en el tiempo) |
| Claridad de Instrucciones | Transcribe (+ reglas sobre el texto) |
| Tiempo Hablando vs. Demostrando | Transcribe + Rekognition |
| Satisfacción del Alumno | Rekognition (rostros/engagement) o Comprehend |

### Tablas de BD que usarás

| Tabla / columna | Uso en AWS |
|-----------------|------------|
| `archivos_media.s3_bucket`, `s3_key` | Ruta del archivo en S3 |
| `analisis_jobs.job_id_externo` | ID del job en Rekognition/Transcribe |
| `analisis_jobs.raw_response` | JSON completo devuelto por AWS |
| `analisis_jobs.status` | pending → submitted → in_progress → completed / failed |
| `metricas.valor_numerico`, `detalle` | Resultado final para el dashboard |
| `clases.status` | pendiente_analisis → analizando → completada / error |

### Variables de entorno (cuando implementes)

Añade a tu `.env` (ver `.env.example`):

| Variable | Descripción |
|----------|-------------|
| `AWS_ENABLED` | `true` para activar el pipeline (default: `false`) |
| `AWS_REGION` | Región, ej. `us-east-1` |
| `AWS_ACCESS_KEY_ID` | Credencial IAM (o usa rol en ECS/EC2) |
| `AWS_SECRET_ACCESS_KEY` | Credencial IAM |
| `S3_BUCKET` | Bucket para videos y audios |

En producción preferible: **rol IAM** del contenedor en lugar de keys en `.env`.

### Dependencia Python

Descomenta en `requirements.txt`:

```text
boto3>=1.34
```

Reconstruye la imagen: `docker compose up --build`.

### Orden de implementación recomendado

1. **S3** — `s3_client.upload_archivo_to_s3`; rellenar `s3_bucket` y `s3_key`.
2. **Transcribe** — primer job real; guardar `raw_response` en `analisis_jobs`.
3. **Extractor** — implementar `extract_claridad_instrucciones` y probar en dashboard.
4. **Rekognition** — video; métricas de asistencia y permanencia.
5. **Métricas compuestas** — hablando vs. demostrando y satisfacción.
6. **Poller o webhook** — `flask aws-poll-jobs` o `POST /webhooks/aws/sns`.
7. Activar en `analysis_service.enqueue_analysis` con `AWS_ENABLED=true`.

### Comandos útiles (fase AWS)

```bash
# Consultar jobs pendientes (cuando job_poller esté implementado)
docker compose exec web flask aws-poll-jobs
```

### Consultar resultados sin Celery

No hace falta Celery ni colas de tareas en el servidor: AWS procesa en la nube. Basta con:

- `docker compose exec web flask aws-poll-jobs` (manual o con cron), o
- Webhook SNS en `POST /webhooks/aws/sns`.

Opcional en producción: **Amazon EventBridge** + **Lambda** en lugar de polling desde Flask.

### Configuración en AWS (consola)

1. Crear bucket S3 (ej. `gymsight-media`) con CORS si el navegador sube directo (opcional).
2. Crear usuario/rol IAM con permisos: `s3:PutObject`, `rekognition:*`, `transcribe:*`.
3. (Opcional) Topic SNS + suscripción HTTPS a `https://tu-dominio/webhooks/aws/sns` para jobs asíncronos.

### Qué no hace falta cambiar

- Modelos de las 7 tablas (ya preparados).
- Plantillas del dashboard (ya muestran métricas `completed` con valor).
- Flujo de subida/edición de clases (solo se activa `enqueue_analysis`).
