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

El flujo tiene dos pasos: **crear la clase recurrente** y **subir sesiones** (grabaciones semanales).

1. **Nueva clase** (`/upload/programa`) — define gimnasio, profesor, tipo, nombre, sala y nivel (sin archivos).
2. Desde el detalle de la clase → **Subir sesión** — elige fecha y sube video y/o audio.
3. Repite el paso 2 cada semana para acumular historial de la misma clase.
4. En **Dashboard** ves las clases recurrentes con el número de sesiones; entra a **Ver historial** para listarlas.

Al arrancar por primera vez (base vacía), la app crea las tablas, aplica migraciones y siembra datos de demostración (1 gimnasio, 3 profesores, 4 tipos de clase y 4 clases de ejemplo enlazadas a videos en S3).

## Restaurar dump con datos analizados (`gymsight_demo.sql`)

El archivo `gymsight_demo.sql` incluye clases **ya analizadas** (jobs AWS, métricas completas). Fue exportado con el esquema **anterior** (sin tabla `programas_clase`). Para usarlo:

**No restaures el dump directamente sobre una base que ya tiene migraciones** — Postgres bloqueará los `DROP TABLE` porque `programas_clase` referencia otras tablas. Hay que recrear la base vacía, restaurar y migrar.

### Comando recomendado

Desde la carpeta del proyecto:

```bash
./docker/restore-demo.sh gymsight_demo.sql
```

El script:

1. Levanta Postgres y detiene `web` (libera conexiones).
2. Recrea la base de datos `gymsight` desde cero.
3. Restaura el dump.
4. Aplica la migración `programas_clase` (cada clase antigua pasa a ser 1 programa + 1 sesión; **métricas y jobs se conservan**).
5. Levanta `web` de nuevo.

Al terminar: **http://localhost:5001**

### Migraciones en arranque normal

Si ya tienes datos en Docker **sin** restaurar un dump, el entrypoint detecta el esquema y aplica migraciones pendientes al levantar `web`. También puedes ejecutarlas a mano:

```bash
docker compose exec web flask db upgrade
```

## Comandos útiles

| Comando | Descripción |
|---------|-------------|
| `docker compose up --build` | Construye y levanta app + base de datos |
| `docker compose up -d` | Levanta en segundo plano |
| `docker compose down` | Detiene y elimina contenedores |
| `docker compose down -v` | Detiene y **borra** datos (BD y uploads) |
| `docker compose logs -f web` | Ver logs de la aplicación |
| `docker compose ps` | Estado de los contenedores |
| `./docker/restore-demo.sh gymsight_demo.sql` | Restaura dump analizado + migración |
| `docker compose exec web flask db upgrade` | Aplica migraciones pendientes |

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
| `programas_clase` | Clase recurrente (p. ej. «Pilates martes 10:00») |
| `clases` | Sesión concreta (una grabación semanal) |
| `archivos_media` | Videos y audios subidos |
| `analisis_jobs` | Jobs de análisis AWS (Rekognition/Transcribe) |
| `metricas` | Las 5 métricas del dashboard (por sesión) |

Cada `programas_clase` agrupa muchas `clases` (sesiones). Cada sesión tiene su propio video, jobs y métricas.

## Métricas: qué miden y cómo se calculan

Las 5 métricas **no son valores arbitrarios**: cada una se deriva de la salida real de
los servicios de AWS (Rekognition, Transcribe, Comprehend) con una fórmula explícita.
La lógica vive en `app/services/analysis/metrics_extractor.py` y cada métrica guarda en
`metricas.detalle` (JSON) los números intermedios que la justifican.

### 1. Asistencia — *personas*

- **Qué mide:** cuántas personas hubo en la clase.
- **Fuente y cálculo:** se toma el **peak (máximo) de caras simultáneas** que Rekognition
  FaceDetection detecta en los tres tercios del video (inicio / mitad / final), y se usa el
  mayor de los tres.
- **Unidad:** número de personas.
- *Detalle guardado:* caras en inicio, mitad y final.

> Fuente original era Rekognition **People Pathing** (conteo de personas únicas), pero AWS
> lo descontinuó (31-oct-2025). El código mantiene ese camino como primario y cae al conteo
> de caras como respaldo (ver flag `REKOGNITION_PERSON_TRACKING_ENABLED`).

### 2. Permanencia — *porcentaje (0–100)*

- **Qué mide:** si los alumnos se quedan hasta el final o la sala se vacía.
- **Cálculo (respaldo FaceDetection):** `caras_al_final / caras_al_inicio × 100` (acotado a 100%).
- **Cálculo (primario PersonTracking, si está disponible):** porcentaje de personas presentes
  durante **≥ 80%** de la duración del video (`UMBRAL_PERMANENCIA_PCT`).
- **Unidad:** %.

### 3. Claridad de Instrucciones — *score 0–100*

Se construye desde los timestamps de cada palabra que devuelve Transcribe. Combina tres
sub-indicadores, cada uno con un rango óptimo (100 puntos dentro del rango, baja linealmente fuera):

| Sub-indicador | Cómo se mide | Rango óptimo | Peso |
|---|---|---|---|
| Palabras por minuto (WPM) | nº palabras / minutos hablados | 120–160 | 50% |
| Longitud media de frase | palabras / nº de frases (frase = corte tras pausa ≥ 1.5 s) | 8–15 palabras | 25% |
| Pausas por minuto | nº de pausas ≥ 1.5 s / minuto | 2–8 | 25% |

`score = 0.5·rango(WPM) + 0.25·rango(longitud_frase) + 0.25·rango(pausas/min)`

- **Unidad:** score 0–100. Si el video no tiene voz → 0.

### 4. Tiempo Hablando vs. Demostrando — *porcentaje hablando*

- **Qué mide:** qué proporción de la clase el profesor pasa hablando vs. demostrando/ejecutando.
- **Cálculo:** se fusionan las palabras contiguas (gap ≤ 0.5 s) en **segmentos de voz**; se suman
  sus duraciones (`segundos_hablando`) y se divide por la duración total del video.
  `% = segundos_hablando / duración_total × 100`. El resto se considera silencio (demostración).
- **Unidad:** % del tiempo hablando (un valor muy alto sugiere que el profesor habla de más).

### 5. Satisfacción del Alumno — *score 0–100*

Score compuesto, **sin encuestas**, a partir de dos señales:

- **Visual (70%)** — emociones faciales de Rekognition: `50 + 50·(positivas − negativas)/total`,
  donde positivas = HAPPY, SURPRISED y negativas = SAD, ANGRY.
- **Textual (30%)** — sentimiento del transcript vía Comprehend: `50 + 50·(positivo − negativo)`.

Si solo hay una de las dos señales, esa pesa 100%. `score = 0.7·visual + 0.3·textual`.

- **Unidad:** score 0–100.

> Cada sesión queda `completada` si las 5 métricas se calcularon, o `completada_parcial`
> si alguna falló (las demás igual se guardan).

## Estructura del proyecto

```
app/
├── routes/              # Pantallas y webhooks
├── services/
│   ├── aws/             # Clientes S3, Rekognition, Transcribe, Comprehend
│   ├── analysis/        # Pipeline, poller, extractores de métricas
│   ├── analysis_service.py   # Punto de entrada: enqueue_analysis()
│   ├── class_service.py
│   ├── programa_service.py
│   └── upload_service.py
docker/
├── entrypoint.sh        # Migraciones + seed al arrancar
└── restore-demo.sh      # Restaurar gymsight_demo.sql
migrations/
docker-compose.yml
Dockerfile
```

---

## Fase AWS — análisis en la nube

El pipeline está **implementado y probado contra AWS real**. Procesa los videos de las
clases (almacenados en S3) y genera las 5 métricas del dashboard automáticamente.

> Documentación detallada en `docs/`:
> - **`PRESENTACION-AWS.md`** — cómo funciona + guion de demo.
> - **`AVANCES-AWS.md`** — bitácora técnica de la implementación.
> - **`DEPLOY.md`** — qué configurar para producción (rol IAM, env vars, etc.).

### Cómo se activa

En `.env`: `AWS_ENABLED=true` + credenciales (o rol IAM) + `S3_BUCKET` + `AWS_REGION`.
Con `AWS_ENABLED=false` la app funciona normal sin tocar AWS (los archivos se guardan local).

### Flujo real

```text
1. Usuario crea la clase recurrente (programa) y sube una sesión (video/audio)
2. El servidor crea la sesión (estado "awaiting_upload") y devuelve URLs PRE-FIRMADAS
3. El navegador sube el video DIRECTO a S3 (no pasa por el servidor)
4. Al terminar, /upload/<id>/complete verifica el objeto en S3 y dispara el análisis
5. pipeline pone la sesión en "analizando" y lanza jobs: Rekognition FaceDetection + Transcribe
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
| Asistencia | Rekognition FaceDetection (peak de caras por tercio del video) |
| Permanencia | Rekognition FaceDetection (caras al final vs. inicio) |
| Claridad de Instrucciones | Transcribe (palabras/min, frases, pausas) |
| Tiempo Hablando vs. Demostrando | Transcribe (segmentos con voz vs. silencio) |
| Satisfacción del Alumno | Rekognition FaceDetection (emociones) + Comprehend (sentimiento) |

**Nota sobre asistencia y permanencia:** AWS **restringe Rekognition People Pathing**
(`StartPersonTracking`), que era su fuente original — devuelve `AccessDenied` a nivel de
cuenta aunque IAM lo permita y el resto de APIs de Rekognition Video funcionen. Por eso el
job está **desactivado por defecto** (`REKOGNITION_PERSON_TRACKING_ENABLED=false`) y ambas
métricas usan el conteo de caras de FaceDetection como fuente. Si AWS te habilita la API,
pon el flag en `true`. Para producción, lo más preciso sería Label Detection ("Person") o
YOLOv9 + ByteTrack en SageMaker (ver `DEPLOY.md`).

**Nota sobre claridad y habla/demo:** Transcribe **detecta el idioma automáticamente**
(`TRANSCRIBE_LANGUAGE_CODE=auto`) entre los candidatos de `TRANSCRIBE_LANGUAGE_OPTIONS`
(es-ES/en-US). Si el video no tiene voz (p. ej. solo música), estas dos métricas salen 0
(correcto).

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
| `REKOGNITION_PERSON_TRACKING_ENABLED` | `true` reactiva el job de PersonTracking (default `false`; AWS restringe esa API, ver nota de asistencia) |
| `BEDROCK_MODEL_ID` | Modelo de Bedrock para los tips IA (default `us.amazon.nova-lite-v1:0`) |
| `BEDROCK_MAX_TOKENS` | Máx. tokens de la respuesta del modelo (default `1024`) |

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
(o al menos FaceDetection), `transcribe:*`, `comprehend:DetectSentiment` y
`bedrock:InvokeModel` + `bedrock:Converse` (para los tips IA).

Para todo lo de producción (rol IAM, RDS, secrets, etc.) ver **`docs/DEPLOY.md`**.

---

## Recomendaciones IA para profesores (Amazon Bedrock / Nova)

Además de las métricas, GymSight genera **tips accionables en lenguaje natural** para cada
profesor, basados en su historial. Aparecen en la vista de detalle del programa, debajo de
los gráficos.

### Cómo funciona

1. El frontend pide async `GET /api/profesores/<id>/recomendaciones`.
2. `recommendation_service` agrega las métricas de **todas las sesiones completadas** del
   profesor (promedio, mín, máx y tendencia comparando primera vs. segunda mitad).
3. Arma un prompt con contexto por métrica e invoca **Amazon Bedrock (Amazon Nova)** vía la
   Converse API (`bedrock_client`).
4. Parsea la respuesta y la devuelve como JSON; el front la pinta en tarjetas.

Las recomendaciones **no se persisten**: se generan bajo demanda y siempre reflejan el estado
más reciente. Se necesitan **≥ 2 sesiones analizadas** del profesor (si no, devuelve
`insufficient_data`).

### Decisiones de diseño

- Usa un **modelo nativo de AWS (Nova)** para que el consumo lo cubran los créditos de AWS;
  configurable con `BEDROCK_MODEL_ID` (`nova-lite` por defecto, `nova-pro` para mayor calidad).
- El prompt está orientado al producto: pide **acciones que el profesor aplica él mismo en
  clase** y **prohíbe sugerir encuestas** o pedir feedback a los alumnos (la propuesta de valor
  es mejorar *sin* encuestas). La salida es texto plano, sin Markdown.
- Si `AWS_ENABLED=false`, el endpoint degrada con elegancia (no rompe la app).

### Módulos

| Archivo | Responsabilidad |
|---------|-----------------|
| `app/services/aws/bedrock_client.py` | Cliente Bedrock (Converse API) |
| `app/services/recommendation_service.py` | Agregación + prompt + parsing + orquestación |
| `app/routes/api.py` | `GET /api/profesores/<id>/recomendaciones` (200/404/503) |
| `app/static/js/recommendations.js` | Fetch + render de las tarjetas |
