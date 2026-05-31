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
| 4 | Transcribe Client | ⬜ Pendiente | — | — |
| 5 | Comprehend Client | ⬜ Pendiente | — | — |
| 6 | *Checkpoint — verificar clientes AWS* | ⬜ Pendiente | (gate, sin PR) | — |
| 7 | Pipeline Orchestrator | ⬜ Pendiente | — | — |
| 8 | Job Poller | ⬜ Pendiente | — | — |
| 9 | Webhook SNS | ⬜ Pendiente | — | — |
| 10 | *Checkpoint — orquestación y completitud* | ⬜ Pendiente | (gate, sin PR) | — |
| 11 | Metrics Extractor — Asistencia y Permanencia | ⬜ Pendiente | — | — |
| 12 | Metrics Extractor — Claridad y Ratio habla/demo | ⬜ Pendiente | — | — |
| 13 | Metrics Extractor — Satisfacción del Alumno | ⬜ Pendiente | — | — |
| 14 | `apply_metrics_to_clase` + estado de clase | ⬜ Pendiente | — | — |
| 15 | *Checkpoint — extracción de métricas* | ⬜ Pendiente | (gate, sin PR) | — |
| 16 | Integración final y verificación end-to-end | ⬜ Pendiente | — | — |
| 17 | *Checkpoint final* | ⬜ Pendiente | (gate, sin PR) | — |

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
_Pendiente._

### Task 5 — Comprehend Client
_Pendiente._

### Task 7 — Pipeline Orchestrator
_Pendiente._

### Task 8 — Job Poller
_Pendiente._

### Task 9 — Webhook SNS
_Pendiente._

### Task 11 — Metrics Extractor: Asistencia y Permanencia
_Pendiente._

### Task 12 — Metrics Extractor: Claridad y Ratio habla/demostración
_Pendiente._

### Task 13 — Metrics Extractor: Satisfacción del Alumno
_Pendiente._

### Task 14 — apply_metrics_to_clase y estado de clase
_Pendiente._

### Task 16 — Integración final y verificación end-to-end
_Pendiente._
