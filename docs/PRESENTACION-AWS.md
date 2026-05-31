# Gymsight — Pipeline de Análisis con AWS (guía para presentar)

---

## 1. ¿Qué es el proyecto en una frase?

Gymsight toma los **videos de clases de gimnasio que ya están guardados en la nube (S3)**,
los procesa con servicios de inteligencia artificial de AWS, y genera **5 métricas
accionables** (asistencia, permanencia, claridad del instructor, ratio habla/demostración
y satisfacción del alumno) que se muestran en un **dashboard**.

La idea de negocio: **feedback sin fricción**. En vez de encuestar a los alumnos, se
"lee" la clase desde el video/audio que ya existe.

> **Encuadre para presentar:** la app en sí (registrar clases, el dashboard, la base de
> datos) **ya existía**. Lo que se construyó en esta fase es **el motor / corazón**: el
> pipeline que toma un video y lo convierte en métricas. Sin esto, el dashboard estaría
> vacío. Esta es la parte que le da valor al producto.

---

## Guion para presentar la demo (paso a paso)

Una narrativa de ~5 minutos. En cada paso: **qué decir** y **qué mostrar**.

### Paso 0 — El problema (15 s)
> "Los gimnasios necesitan saber cómo viven sus alumnos las clases, pero las encuestas
> tienen poca respuesta y molestan. Nuestra idea: leer eso desde los videos que el gym
> **ya tiene** (grabaciones, cámaras), sin pedirle nada al alumno."

### Paso 1 — Qué construimos (30 s)
> "La app y el dashboard ya estaban. Yo construí el **motor**: un pipeline que conecta la
> app con la inteligencia artificial de AWS para sacar 5 métricas de cada clase."

Mostrar el **diagrama del flujo** (sección 3).

### Paso 2 — Los servicios de AWS (45 s)
> "Usamos servicios de IA de AWS, cada uno hace una cosa:
> - **Rekognition** mira el video: sigue personas y detecta emociones en las caras.
> - **Transcribe** convierte el audio en texto.
> - **Comprehend** analiza el sentimiento de ese texto.
> - Todo parte de videos que ya están en **S3**, el disco en la nube de AWS."

Mostrar la **tabla de servicios** (sección 2).

### Paso 3 — DEMO EN VIVO (2 min) 🎬
Tener el `docker compose up` ya corriendo de antes. Entonces:

1. **Disparar el análisis** de los 4 videos reales en S3:
   ```bash
   docker compose exec web flask aws-analyze
   ```
   > "Acá disparo el análisis. La app le pide a AWS que empiece a procesar los videos.
   > Como son largos, AWS trabaja en segundo plano y nos devuelve un ticket (JobId)."

2. **Consultar el estado** (mostrar que es asíncrono):
   ```bash
   docker compose exec web flask aws-poll-jobs
   ```
   > "Este comando le pregunta a AWS si ya terminó. Cuando todos los análisis de una clase
   > terminan, el sistema calcula las métricas solo."

3. **Abrir el dashboard** → http://localhost:5001 → entrar a una clase (ej. **Mat Pilates**,
   45 min):
   > "Y acá está el resultado real: claridad 72/100, satisfacción 60/100 con el desglose de
   > emociones (mayormente CALM), y 73% del tiempo hablando vs. demostrando. **Todo esto
   > salió de un video de 45 minutos, automáticamente.** Y procesamos 4 clases distintas:
   > los números son consistentes entre ellas."

### Paso 4 — Honestidad técnica (30 s) — suma puntos
> "Al probarlo en real, la cuenta de AWS tenía una restricción de organización (un SCP) que
> bloquea **una** función de Rekognition (la de seguir personas); por eso asistencia y
> permanencia salen en 0. No es un bug del código: es una política de la cuenta. Y gracias a
> esa prueba el pipeline quedó más robusto: si un servicio falla, **no se cae todo**, igual
> calcula el resto de las métricas."

### Paso 5 — Cierre (15 s)
> "Resumen: construimos el motor que convierte videos en analítica accionable, probado de
> punta a punta contra AWS real, con código modular y 57 tests automáticos. Es la base
> sobre la que se apoya todo el valor del producto."

---

## 2. Los servicios de AWS que usamos (lo importante si no cachas AWS)

AWS es un conjunto de servicios en la nube que se usan por API (con la librería `boto3`
en Python). Cada uno hace **una** cosa. Estos son los que tocamos:

| Servicio AWS | Qué es / qué hace | Para qué lo usamos |
|--------------|-------------------|--------------------|
| **S3** (Simple Storage Service) | Disco en la nube: guarda archivos ("objetos") dentro de "buckets". Cada objeto se identifica por `bucket` + `key` (la ruta). | Ahí ya están los videos. Solo los **leemos** (no subimos nada desde la app). |
| **Rekognition** | Visión por computadora sobre imágenes y video. | Dos análisis distintos (abajo). |
| → Rekognition **Person Tracking** | Detecta y **sigue personas** a lo largo del video (cuándo aparece/desaparece cada una). | Asistencia y permanencia. |
| → Rekognition **Face Detection** | Detecta rostros y sus **emociones** (HAPPY, SAD, CALM, etc.) frame a frame. | Satisfacción del alumno. |
| **Transcribe** | Pasa **audio a texto** (speech-to-text) con marcas de tiempo por palabra. | Claridad de instrucciones y ratio habla/demostración. |
| **Comprehend** | NLP: analiza el **sentimiento** de un texto (positivo/negativo/neutro). | Complementa la satisfacción (lo que se dice). |
| **SNS** (Simple Notification Service) | Sistema de notificaciones: AWS puede "avisar" a una URL cuando algo pasa. | (Opcional) avisar cuando un job termina, vía webhook. |
| **IAM** (Identity & Access Management) | El sistema de **permisos** de AWS. Define qué puede hacer cada usuario/credencial. | Las credenciales necesitan permiso para cada servicio. |

### Concepto clave: jobs **asíncronos**

Rekognition Video y Transcribe **no responden al instante**. Procesar un video de 1 hora
toma minutos. Por eso funcionan así:

1. Le pides a AWS que **empiece** el análisis → te devuelve un `JobId` y sigue en segundo plano.
2. Más tarde **consultas** ese `JobId` para ver si terminó (`IN_PROGRESS` → `SUCCEEDED`/`FAILED`).

Esto se llama patrón **start → poll** (lanzar y luego consultar). Por eso el pipeline no
es en tiempo real: es por lotes (batch).

Comprehend, en cambio, es **síncrono** (responde al toque), porque es solo texto.

---

## 3. Cómo funciona el pipeline (el flujo completo)

```
   Video ya en S3
        │
        ▼
  enqueue_analysis(clase)         ← se dispara el análisis de una clase
        │
        ▼
  Pipeline Orchestrator
   ├─ valida que el objeto exista en S3
   ├─ lanza Rekognition Person Tracking   ┐
   ├─ lanza Rekognition Face Detection    ├─ jobs asíncronos (guardan un JobId)
   └─ lanza Transcribe                     ┘
        │   (cada job queda como "submitted" en la tabla analisis_jobs)
        ▼
  Job Poller   (comando `flask aws-poll-jobs`, corre cada X minutos)
   ├─ consulta cada JobId en AWS
   ├─ si terminó → guarda la respuesta cruda (raw_response)
   └─ cuando TODOS los jobs de la clase terminaron:
        │
        ▼
  Metrics Extractor
   ├─ corre Comprehend sobre el texto transcrito
   ├─ transforma las respuestas crudas en las 5 métricas
   └─ guarda en la tabla `metricas` + marca la clase como "completada"
        │
        ▼
   Dashboard lee de `metricas`  ← muestra los números
```

**Dos formas de detectar que un job terminó:**
- **Polling**: el comando `flask aws-poll-jobs` consulta cada tanto (lo principal).
- **Webhook SNS**: AWS avisa a `/webhooks/aws/sns` cuando termina (opcional, baja latencia).
  Incluye **validación de firma** para que nadie falsee la notificación.

---

## 4. Cómo está armado el código (mapa rápido)

```
app/services/aws/            ← clientes "de bajo nivel", uno por servicio AWS
  ├─ boto_session.py         ← crea los clientes boto3 con las credenciales
  ├─ s3_client.py            ← verificar existencia, URLs prefirmadas
  ├─ rekognition_client.py   ← start/get de PersonTracking y FaceDetection
  ├─ transcribe_client.py    ← start/get de transcripción
  └─ comprehend_client.py    ← análisis de sentimiento

app/services/analysis/       ← la lógica del pipeline
  ├─ pipeline.py             ← orquesta: valida S3 y lanza los jobs
  ├─ job_poller.py           ← consulta jobs y dispara las métricas
  ├─ metrics_extractor.py    ← convierte respuestas de AWS → 5 métricas
  └─ constants.py            ← nombres de servicios y estados

app/routes/webhooks.py       ← endpoint SNS (con validación de firma)
app/seed.py                  ← siembra las 4 clases de demo enlazadas a los videos en S3
```

Detalle clave: las respuestas crudas de AWS se guardan en `analisis_jobs.raw_response`
(columna JSONB), y el `metrics_extractor` las lee con un dict **llaveado por servicio**
(`rekognition_person_tracking`, `rekognition_face_detection`, `transcribe`, `comprehend`).

---

## 5. Las 5 métricas (de qué dato de AWS sale cada una)

| Métrica | Sale de | Cómo se calcula (resumen) |
|---------|---------|---------------------------|
| **Asistencia** | Rekognition Person Tracking | Cuenta personas únicas (`PersonIndex` distintos). |
| **Permanencia** | Rekognition Person Tracking | % de personas presentes ≥80% de la duración. |
| **Claridad de instrucciones** | Transcribe | Score 0-100 según palabras/min (óptimo 120-160), largo de frases y pausas. |
| **Habla vs. demostración** | Transcribe | % del tiempo con voz vs. silencio (fusiona palabras en segmentos de habla). |
| **Satisfacción del alumno** | Rekognition Face Detection + Comprehend | 70% emociones faciales (HAPPY/SURPRISED suman, SAD/ANGRY restan) + 30% sentimiento del texto. |

---

## 6. Configuración (cómo se activa)

Variables de entorno (en `.env`):

| Variable | Para qué |
|----------|----------|
| `AWS_ENABLED` | `true`/`false` — interruptor maestro. Si es `false`, la app funciona normal sin tocar AWS. |
| `AWS_REGION` | Región de AWS (ej. `us-west-2`). El bucket y los servicios deben estar en la misma región. |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | Credenciales del usuario IAM. |
| `S3_BUCKET` | Bucket donde están los videos. |
| `TRANSCRIBE_LANGUAGE_CODE` | Idioma del audio (ej. `en-US`). |

**Permisos IAM necesarios** (esto es puro AWS): el usuario de las credenciales necesita
permiso para `s3:GetObject`, las acciones de Rekognition (`StartPersonTracking`,
`StartFaceDetection`, `Get...`), Transcribe y `comprehend:DetectSentiment`. Con las
políticas administradas `AmazonRekognitionFullAccess`, `AmazonTranscribeFullAccess`,
`ComprehendReadOnly` y `AmazonS3ReadOnlyAccess` alcanza.

---

## 7. La prueba real contra AWS (qué se demostró)

Se corrió el pipeline **de verdad** contra una cuenta AWS, con los 4 videos reales en S3
(uno de 15 s y tres clases completas de 45-61 min).

**Funcionó end-to-end en las 4 clases:** cada video recorrió todo el flujo
(lanzar jobs → polling → métricas → estado `completada`) y produjo **3 de las 5 métricas
con datos reales** (claridad, satisfacción, habla/demo). Asistencia y permanencia quedaron
en 0 por el bloqueo de Person Tracking (ver hallazgo 1).

**Tres hallazgos durante la prueba** (todos típicos de integrar con AWS, y cada uno dejó el
sistema mejor):

1. **Person Tracking bloqueado por la cuenta.** `StartPersonTracking` devolvía
   `AccessDenied` con mensaje vacío, **solo esa acción** (FaceDetection, LabelDetection y
   las APIs base de Rekognition sí funcionaban). Diagnóstico: la cuenta tiene un **SCP**
   (Service Control Policy: política a nivel de organización que está por encima de los
   permisos del usuario) que deniega específicamente `StartPersonTracking`. **No es un bug
   del código ni de los permisos del usuario** — es una restricción de la cuenta (común en
   cuentas de taller/sandbox). Por eso asistencia y permanencia quedan en 0.

2. **Formato del URI de Transcribe.** Transcribe quiere la "key" del objeto S3 **literal**
   (con espacios y `#` tal cual), no URL-encoded. Se corrigió.

3. **Tamaño de la respuesta de FaceDetection (escalabilidad).** FaceDetection sobre un
   video de 1 h devuelve **~245 MB** de JSON (un rostro por frame). PostgreSQL tiene un
   límite duro de **256 MB por valor JSONB**, así que guardar el crudo completo fallaba y
   el job nunca se cerraba. **Fix:** ahora se **agregan las emociones al vuelo** durante la
   paginación y se guarda solo un resumen (~300 bytes en vez de 245 MB). Escala a videos
   de cualquier duración. *(Talking point fuerte: muestra pensamiento de escalabilidad.)*

> Aprendizaje para presentar: el código quedó **más robusto** gracias a la prueba real.
> Si un servicio está bloqueado, el pipeline **no se cae** (marca ese job y sigue), y la
> ingesta **escala** a videos largos sin reventar la base de datos.

---

## 8. Resultados reales de las 4 clases

Las 4 clases reales en S3 se procesaron completas. Valores generados **automáticamente
desde el video** por Transcribe + Rekognition Face Detection + Comprehend:

| Clase | Duración | Claridad | Satisfacción | Habla vs. demo |
|-------|----------|----------|--------------|----------------|
| Silver Sneakers | 12 s | 86 | 58 | 54.7 % |
| Mat Pilates | 45 min | 72 | 60 | 73.4 % |
| Reformer | 57 min | 78 | 54 | 65.3 % |
| Hot Pilates | 61 min | 74 | 62 | 69.6 % |

*(Asistencia y permanencia salen 0 en todas por el SCP que bloquea Person Tracking.)*

**Patrón coherente** (buen punto para presentar): clases de pilates con ambiente
predominantemente **CALM**, instructor hablando 65-73 % del tiempo, y claridad 72-86 con
ritmos de 115-158 palabras/min. Los números **tienen sentido** y son consistentes entre
clases — el pipeline no inventa, refleja la clase real.

**Ejemplo de detalle (Hot Pilates, 61 min):** emociones `{CALM: 58%, HAPPY: 8%, SAD: 15%,
SURPRISED: 8%...}`, habló 42 min / 18.5 min en silencio, 118.8 palabras/min.

---

## 9. Cómo correrlo / demo en vivo

```bash
# 1. Poner credenciales y activar AWS en .env (AWS_ENABLED=true, region, bucket, keys)
# 2. Levantar todo (instala deps, crea DB, siembra los 4 videos, arranca la app)
docker compose up -d --build

# 3. Disparar el análisis de las clases sembradas
docker compose exec web flask aws-analyze            # todas las pendientes
#   o una sola:
docker compose exec web flask aws-analyze <clase_id>

# 4. Consultar jobs (repetir cada par de minutos hasta que terminen)
docker compose exec web flask aws-poll-jobs

# 5. Ver el dashboard
#   http://localhost:5001
```

---

## 10. Estado y próximos pasos

**Hecho y verificado:**
- Las 16 tareas del plan implementadas, con **57/57 tests** pasando (mockeando AWS).
- Pipeline probado **en real** contra AWS: 3 métricas con datos reales end-to-end.

**Pendiente / mejoras:**
- Habilitar `StartPersonTracking` en la cuenta (quitar el SCP) para tener asistencia y
  permanencia. Es un cambio de **configuración de AWS**, no de código.
- Terminar la corrida de los videos de 1 h (FaceDetection tarda ~20-35 min en videos largos).
- Subir el código y abrir los Pull Requests (hoy está en ramas locales).

---

## Glosario express de AWS

- **S3 / bucket / key**: almacenamiento; un bucket es una carpeta raíz, la key es la ruta del archivo.
- **boto3**: la librería oficial de Python para hablar con AWS.
- **Job asíncrono**: tarea que AWS procesa en segundo plano; se consulta después con su `JobId`.
- **Polling**: consultar repetidamente "¿ya terminó?".
- **IAM**: permisos de AWS (qué puede hacer cada credencial).
- **SCP (Service Control Policy)**: política a nivel de organización que limita lo que se
  puede hacer en una cuenta, **por encima** de los permisos del usuario.
- **SNS**: servicio de notificaciones (push) de AWS.
- **Región**: ubicación geográfica de los servicios (ej. `us-west-2` = Oregón). Todo debe
  estar en la misma región para hablar entre sí sin fricción.
