# Avances — Integración del Pipeline AWS

Documento vivo para registrar el avance de la fase AWS de Gymsight. Cada task de nivel 1 del plan (`.kiro/specs/aws-pipeline-integration/tasks.md`) se implementa en su propia rama y se integra mediante un Pull Request.

## Flujo de trabajo (Git)

- **Rama de integración:** `aws-analisis` (sale de `main`). Protege el estado actual de `main`.
- **Una rama por task:** `task-<n>-<slug>` sale de `aws-analisis`.
- **Un PR por task:** cada rama de task se integra con un PR hacia `aws-analisis`.
- **Merge final:** al terminar toda la fase, un único PR `aws-analisis` → `main`.

> ⚠️ **Acceso:** la cuenta `camila-hinojosa-anez` hoy solo tiene permiso de lectura sobre `RolandCSCHC/Emprendimiento-Proyecto`. Hasta obtener acceso de escritura (o crear un fork), las ramas se mantienen **locales y apiladas** (cada task sale de la anterior) para que el código siempre compile. Al obtener acceso se pushean y se abren los PRs en orden.

```
main
 └── aws-analisis            (integración)
      ├── task-1-config      → PR → aws-analisis
      ├── task-2-s3-client   → PR → aws-analisis
      └── ...                → PR → aws-analisis
                              ⇒ PR final aws-analisis → main
```

## Estado general

| Task | Descripción | Estado | Rama | PR |
|------|-------------|--------|------|----|
| 1 | Configuración del proyecto y dependencias AWS | 📦 Commit local | `task-1-config` | — |
| 2 | S3 Client | 📦 Commit local | `task-2-s3-client` | — |
| 3 | Rekognition Client | 📦 Commit local | `task-3-rekognition` | — |
| 4 | Transcribe Client | 📦 Commit local | `task-4-transcribe` | — |
| 5 | Comprehend Client | 📦 Commit local | `task-5-comprehend` | — |
| 6 | *Checkpoint — verificar clientes AWS* | ⬜ Pendiente | (gate, sin PR) | — |
| 7 | Pipeline Orchestrator | 📦 Commit local | `task-7-pipeline` | — |
| 8 | Job Poller | 📦 Commit local | `task-8-job-poller` | — |
| 9 | Webhook SNS | 📦 Commit local | `task-9-webhook` | — |
| 10 | *Checkpoint — orquestación y completitud* | ⬜ Pendiente | (gate, sin PR) | — |
| 11 | Metrics Extractor — Asistencia y Permanencia | 📦 Commit local | `task-11-metrics-asistencia` | — |
| 12 | Metrics Extractor — Claridad y Ratio habla/demo | 📦 Commit local | `task-12-metrics-claridad` | — |
| 13 | Metrics Extractor — Satisfacción del Alumno | 📦 Commit local | `task-13-metrics-satisfaccion` | — |
| 14 | `apply_metrics_to_clase` + estado de clase | 📦 Commit local | `task-14-apply-metrics` | — |
| 15 | *Checkpoint — extracción de métricas* | ⬜ Pendiente | (gate, sin PR) | — |
| 16 | Integración final y verificación end-to-end | 📦 Commit local | `task-16-integracion` | — |
| 17 | *Checkpoint final* | ✅ 57/57 | (gate, sin PR) | — |

**Leyenda:** ⬜ Pendiente · 🟡 En progreso · 📦 Commit local (pendiente push/PR) · ✅ Mergeado

---

## Bitácora por task

> Cada task completada documenta aquí: qué se hizo, archivos tocados, decisiones y cómo se verificó.

### Task 1 — Configuración del proyecto y dependencias AWS
🟡 En progreso (rama `task-1-config`).

**Qué se hizo:**
- `requirements.txt`: agregadas deps `boto3>=1.34`, `requests>=2.31` (firma SNS) y deps de test `pytest>=8.0`, `moto>=5.0`.
- `app/config.py`: nuevas variables `SNS_TOPIC_ARN`, `TRANSCRIBE_OUTPUT_BUCKET`, `TRANSCRIBE_LANGUAGE_CODE` (default `es-ES`). Nueva `TestingConfig` (TESTING=True, AWS deshabilitado, DB de test) registrada como `"testing"`.
- `app/services/aws/boto_session.py` (nuevo): `get_boto_client(service_name)` — crea clientes boto3 con la config; usa access keys si existen, si no la cadena de credenciales por defecto (rol IAM). Import de boto3 perezoso para degradación elegante.
- `.env.example`: documentadas `SNS_TOPIC_ARN`, `TRANSCRIBE_OUTPUT_BUCKET`, `TRANSCRIBE_LANGUAGE_CODE`.
- `tests/conftest.py` + `pytest.ini` (nuevos): scaffolding de tests con fixtures `app` y `client`.
- `app/seed.py`: ahora crea 4 clases de demo (una por video real en S3), enlazando `ArchivoMedia.s3_bucket`/`s3_key` a los objetos existentes. El bucket se toma de `S3_BUCKET` (config); las keys son los nombres reales de los 4 videos.

**Decisiones:**
- Idioma de Transcribe configurable vía `TRANSCRIBE_LANGUAGE_CODE` (los 4 videos de demo están en inglés → `en-US`).
- DB de test por defecto SQLite en memoria; tests que toquen DB con tipos PostgreSQL (UUID/JSONB) usarán `TEST_DATABASE_URL` apuntando a Postgres.

**Verificación:** `python -m py_compile` OK. Tests reales (pytest) requieren instalar deps o correr en Docker — se valida en el Checkpoint (Task 6).

**Datos reales de la demo:** bucket `rekognition-gym-videos`, región `us-west-2` (Oregon), idioma `en-US`. Configurados en `.env.example`; las credenciales AWS van en `.env` (no versionado).

### Task 2 — S3 Client
📦 Commit local (rama `task-2-s3-client`, sobre `task-1-config`).

**Qué se hizo (`app/services/aws/s3_client.py`):**
- `check_object_exists(bucket, key)`: usa `head_object`; devuelve `False` ante 404/NoSuchKey/NotFound, re-lanza otros errores.
- `get_s3_uri(bucket, key)`: devuelve `s3://bucket/key` (sin cambios).
- `generate_presigned_url(bucket, key, expires_in=3600)`: URL pre-firmada `get_object`; `None` si falla.
- Eliminado el stub huérfano `upload_archivo_to_s3` (decisión de diseño: sin upload desde la app).
- Usa `get_boto_client("s3")` de la Task 1.

**Tests (`tests/test_s3_client.py`, con `moto`):** existencia True/False, `get_s3_uri`, y generación de URL pre-firmada.

**Verificación:** `python -m py_compile` OK. Ejecución de pytest pendiente de entorno con deps (Checkpoint Task 6).

### Task 3 — Rekognition Client
📦 Commit local (rama `task-3-rekognition`, sobre `task-2-s3-client`).

**Qué se hizo (`app/services/aws/rekognition_client.py`):**
- Refactor de la interfaz: se reemplazan `start_video_analysis`/`get_video_job_result` por 4 funciones específicas.
- `start_person_tracking(bucket, key, sns_topic_arn=None)` → `JobId`.
- `start_face_detection(bucket, key, sns_topic_arn=None)` con `FaceAttributes='ALL'` → `JobId`.
- `get_person_tracking_result(job_id)` → `{status, raw, persons}` (paginando `NextToken`).
- `get_face_detection_result(job_id)` → `{status, raw, faces}` (paginando). Incluye `error` si el job falló.
- `NotificationChannel` (SNS) solo si hay topic **y** `REKOGNITION_SNS_ROLE_ARN` (Rekognition exige RoleArn); si no, se resuelve por polling.
- `app/services/aws/__init__.py`: actualizado a los nuevos nombres (la limpieza del `upload_archivo_to_s3` se reincorporó al commit de la Task 2).

**Tests (`tests/test_rekognition_client.py`):** inicio de ambos jobs, consulta en progreso, completado con paginación, y fallido (mockeando el cliente boto3).

**Verificación:** `python -m py_compile` OK. pytest pendiente de entorno (Checkpoint Task 6).

### Task 4 — Transcribe Client
📦 Commit local (rama `task-4-transcribe`, sobre `task-3-rekognition`).

**Qué se hizo (`app/services/aws/transcribe_client.py`):**
- `start_transcription(s3_uri, language_code="es-ES", output_bucket=None)`: genera nombre único `gymsight-{uuid}`, lanza `start_transcription_job` con `Settings.ShowSpeakerLabels=False`, deriva `MediaFormat` de la extensión y acepta cualquier idioma. Retorna el nombre del job.
- `get_transcription_result(job_name)`: consulta el job y, si terminó, descarga el JSON de resultados (con `requests`). Retorna `{status, transcript, raw}`; `error` si falló.
- Normalización de estado: Transcribe usa `COMPLETED` → se mapea a `SUCCEEDED` para unificar con Rekognition y el poller.

**Tests (`tests/test_transcribe_client.py`):** inicio con 3 idiomas (es-ES/en-US/pt-BR), en progreso, completado (con descarga mockeada) y fallido.

**Verificación:** `python -m py_compile` OK. pytest pendiente de entorno (Checkpoint Task 6).

### Task 5 — Comprehend Client
📦 Commit local (rama `task-5-comprehend`, sobre `task-4-transcribe`).

**Qué se hizo (`app/services/aws/comprehend_client.py`):**
- Renombrado el stub `analyze_text_sentiment` → `analyze_sentiment(text, language_code="es")`.
- Texto vacío o < 10 caracteres → NEUTRAL con confianza 0 (sin llamar a la API).
- Trunca el texto a 5000 bytes (límite de `detect_sentiment`).
- Retorna `{sentiment, scores{positive,negative,neutral,mixed}, confidence, raw}`.
- `app/services/aws/__init__.py`: exporta `analyze_sentiment`.

**Tests (`tests/test_comprehend_client.py`):** texto vacío/corto neutro, texto normal con scores, y truncado a 5000 bytes.

**Decisión / simplificación:** para la demo se analiza el sentimiento de los primeros 5000 bytes del transcript (no se hace chunking del audio completo).

**Verificación:** `python -m py_compile` OK. pytest pendiente de entorno (Checkpoint Task 6).

---

## Checkpoint Task 6 — Verificar clientes AWS individuales ✅
Bloque de clientes AWS (Tasks 1–5) implementado y verificado.

**Resultado:** `pytest` ejecutado en Docker (imagen `gymsight-test` con deps de `requirements.txt`) → **20/20 tests pasan** (`0.87s`).

```
docker build -t gymsight-test .
docker run --rm --entrypoint pytest gymsight-test -v
```

**Fix aplicado:** se agregó `pythonpath = .` a `pytest.ini` para que pytest encuentre el paquete `app` (scaffolding de la Task 1, detectado al correr la suite).

### Task 7 — Pipeline Orchestrator
📦 Commit local (rama `task-7-pipeline`, sobre `task-5-comprehend`).

**Qué se hizo:**
- `app/services/analysis/constants.py` (nuevo): nombres de servicio (llaves de `combined_raw_data`) y estados de job/clase/métrica.
- `app/services/analysis/pipeline.py`: `start_analysis_for_clase` — no-op si AWS deshabilitado; pone clase en `analizando`; por archivo valida S3 y lanza jobs (video → person_tracking + face_detection + transcribe; audio → transcribe); registra `AnalisisJob` (`submitted` o `failed`) con `request_payload`. Si un archivo falla no detiene los demás (req 5.7). URL-encode de la key para el `MediaFileUri` de Transcribe (los nombres traen espacios y `#`).
- `app/services/analysis_service.py`: `enqueue_analysis` activado (verifica `AWS_ENABLED` y llama al orquestador).
- `app/__init__.py`: `_validate_aws_config` — si `AWS_ENABLED` y falta `AWS_REGION`/`S3_BUCKET`, loguea error y deshabilita el pipeline (req 14.3).

**Tests (`tests/test_pipeline.py` + `tests/factories.py`):** AWS deshabilitado no-op, video lanza 3 jobs, audio solo transcribe, archivo sin S3 → failed, objeto inexistente → failed. Requieren DB Postgres (`db_session`).

**Verificación:** sintaxis OK. pytest con DB se corre en el Checkpoint 10.

### Task 8 — Job Poller
📦 Commit local (rama `task-8-job-poller`, sobre `task-7-pipeline`).

**Qué se hizo (`app/services/analysis/job_poller.py`):**
- `poll_pending_jobs()`: consulta jobs `submitted`/`in_progress`, los actualiza y retorna el conteo. Mapea `servicio` → getter del cliente AWS (`_GETTERS`).
- `_refresh_job`: SUCCEEDED → guarda `raw_response` (el dict del getter) + `completed`; FAILED → `error_mensaje` + `failed` + clase a `error`; si no, `in_progress`.
- `_maybe_extract_metrics`: cuando **todos** los jobs de una clase están `completed`, arma `combined_raw_data` (llaveado por servicio) y llama `apply_metrics_to_clase`.
- `process_completed_job(id)`: refresca un job puntual (webhook SNS) y dispara métricas si corresponde.
- El comando `flask aws-poll-jobs` (ya registrado) ahora ejecuta sin `NotImplementedError`.

**Tests (`tests/test_job_poller.py`):** en progreso, completado (guarda raw + dispara métricas), fallido (clase a error), y `process_completed_job`. Mockean los getters y `apply_metrics_to_clase`.

**Verificación:** sintaxis OK. pytest con DB se corre en el Checkpoint 10.

### Task 9 — Webhook SNS
📦 Commit local (rama `task-9-webhook`, sobre `task-8-job-poller`).

**Qué se hizo (`app/routes/webhooks.py`):**
- `POST /webhooks/aws/sns`: parsea el cuerpo, valida la firma y enruta por tipo.
- `_verify_sns_signature`: descarga el certificado X.509 (solo hosts `*.amazonaws.com`, anti-SSRF), arma el string canónico según el tipo y verifica la firma RSA (SHA1 v1 / SHA256 v2). Firma inválida → 403.
- `SubscriptionConfirmation`: hace GET a `SubscribeURL` y responde 200.
- `Notification`: extrae `JobId` del `Message`, busca el `AnalisisJob` y llama `process_completed_job`; 400 si no hay job_id válido o no se encuentra.
- `requirements.txt`: + `cryptography>=42.0` (verificación de firma).

**Tests (`tests/test_webhooks.py`):** JSON inválido (400), firma inválida (403), SubscriptionConfirmation (200 + GET), Notification procesa job (200), sin job_id (400), job inexistente (400).

**Verificación:** sintaxis OK. pytest con DB en el Checkpoint 10.

### Task 11 — Metrics Extractor: Asistencia y Permanencia
📦 Commit local (rama `task-11-metrics-asistencia`, sobre `task-9-webhook`).

**Qué se hizo (`app/services/analysis/metrics_extractor.py`):**
- Helpers compartidos: `_index_timeline` (por `PersonIndex`: primera/última aparición y confianzas), `_video_duration_ms`, `_avg`.
- `extract_asistencia`: cuenta personas únicas; `valor_numerico` = N, `confianza` promedio, `detalle.personas_detectadas`.
- `extract_permanencia`: % de personas presentes ≥80% de la duración; `detalle.timeline` con `salida_ms` por persona; umbral 80.
- Los extractores 12/13 quedan como stubs hasta sus tasks.

**Tests (`tests/test_metrics_asistencia.py`):** sin personas, conteo único + confianza, permanencia completa, mixta (50%), sin datos. **5/5 pasan** (funciones puras, sin DB).

**Verificación:** `pytest tests/test_metrics_asistencia.py` → 5 passed.

### Task 12 — Metrics Extractor: Claridad y Ratio habla/demostración
📦 Commit local (rama `task-12-metrics-claridad`, sobre `task-11-metrics-asistencia`).

**Qué se hizo (`metrics_extractor.py`):**
- Helpers: `_transcribe_words` (palabras pronunciadas con start/end/conf), `_rango_score` (100 dentro del rango, decae fuera).
- `extract_claridad_instrucciones`: WPM, longitud de frase (separadas por pausa ≥1.5s) y pausas/min → score 0-100 (0.5·WPM + 0.25·frase + 0.25·pausas); rango óptimo 120-160 WPM.
- `extract_tiempo_hablando_vs_demostrando`: fusiona palabras (gap ≤0.5s) en segmentos de habla; calcula segundos hablando/silencio y % sobre la duración (de PersonTracking o última palabra).

**Tests (`tests/test_metrics_claridad.py`):** sin palabras, ritmo óptimo (score ≥90), ritmo lento (<50), tiempo con duración de video, y usando la última palabra. **6/6 pasan.**

**Verificación:** `pytest tests/test_metrics_claridad.py` → 6 passed.

### Task 13 — Metrics Extractor: Satisfacción del Alumno
📦 Commit local (rama `task-13-metrics-satisfaccion`, sobre `task-12-metrics-claridad`).

**Qué se hizo (`metrics_extractor.py`):**
- Helpers: `_clamp`, `_agregar_emociones` (suma confianza por emoción + confianzas de rostro), `_combinar_scores` (70% visual / 30% textual según disponibilidad).
- `extract_satisfaccion_alumno`: pondera emociones (HAPPY/SURPRISED positivas, SAD/ANGRY negativas) → score visual 0-100; si hay Comprehend, combina 70/30 con el score textual. Sin datos → 0 con confianza 0.

**Tests (`tests/test_metrics_satisfaccion.py`):** solo visual positivo/negativo, visual+textual (92), solo textual, y sin datos. **5/5 pasan.**

**Verificación:** `pytest tests/test_metrics_satisfaccion.py` → 5 passed.

### Task 14 — apply_metrics_to_clase y estado de clase
📦 Commit local (rama `task-14-apply-metrics`, sobre `task-13-metrics-satisfaccion`).

**Qué se hizo (`metrics_extractor.py`):**
- `apply_metrics_to_clase`: corre Comprehend sobre el transcript (convierte `es-ES`→`es`), ejecuta los 5 extractores, hace upsert en `metricas` (`_guardar_metrica`, por `clase_id`+`clave`). Si un extractor falla, marca esa métrica `failed` y sigue.
- Estado de clase: todas completas → `completada`; alguna falla → `completada_parcial`; actualiza `updated_at`.

**Tests (`tests/test_apply_metrics.py`):** las 5 métricas completan → clase `completada`; un fallo → `completada_parcial`; upsert idempotente (no duplica). Mockea Comprehend.

**Verificación:** ver Checkpoint 15.

---

## Checkpoint Task 15 — Verificar extracción de métricas ✅
Bloque de métricas (Tasks 11–14) implementado y verificado.

**Resultado:** suite completa contra **Postgres** → **54/54 tests pasan** (`2.66s`).

---

### Task 16 — Integración final y verificación end-to-end
📦 Commit local (rama `task-16-integracion`, sobre `task-14-apply-metrics`).

**Qué se hizo (`tests/test_integration.py`):**
- AWS deshabilitado: `enqueue_analysis` es no-op y la app arranca sin credenciales (la fixture `app` usa `AWS_ENABLED=false`).
- CLI `flask aws-poll-jobs` ejecuta sin error y reporta `Jobs procesados: 0` cuando no hay jobs.
- Flujo completo: `enqueue` (3 jobs) → `poll` (todos SUCCEEDED) → 5 métricas `completed` → clase `completada`, con todos los servicios AWS mockeados.

## Checkpoint Task 17 — Final ✅
**Toda la fase AWS implementada y verificada.** Suite completa contra Postgres → **57/57 tests pasan** (`2.90s`).

El pipeline queda funcional de punta a punta: video en S3 → Rekognition/Transcribe → polling/webhook → Comprehend + 5 métricas → tabla `metricas` → dashboard. Pendiente solo: push de las ramas y apertura de PRs cuando haya acceso de escritura, y la corrida real contra AWS con credenciales en `.env`.

## Checkpoint Task 10 — Verificar orquestación y detección de completitud ✅
Bloque de orquestación (Tasks 7–9) implementado y verificado.

**Resultado:** suite completa contra **Postgres** → **35/35 tests pasan** (`2.14s`).

```
docker build -t gymsight-test .
docker network create gymsight-net
docker run -d --name gymsight-pg --network gymsight-net \
  -e POSTGRES_USER=gymsight -e POSTGRES_PASSWORD=gymsight -e POSTGRES_DB=gymsight postgres:16-alpine
docker run --rm --network gymsight-net \
  -e TEST_DATABASE_URL=postgresql://gymsight:gymsight@gymsight-pg:5432/gymsight \
  --entrypoint pytest gymsight-test -q
```

---

### Task 16 — Integración final y verificación end-to-end
_Pendiente._
