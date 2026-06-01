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
> - **Rekognition** mira el video: cuenta personas (por sus caras) y detecta emociones.
> - **Transcribe** convierte el audio en texto (detecta el idioma solo: español o inglés).
> - **Comprehend** analiza el sentimiento de ese texto.
> - Todo se guarda en **S3**, el disco en la nube de AWS."

Mostrar la **tabla de servicios** (sección 2).

### Paso 3 — DEMO EN VIVO (2-3 min) 🎬
Tener `docker compose up` corriendo, **idealmente con el dump de demo ya restaurado**
(`gymsight_demo.sql`), así hay clases analizadas listas para mostrar.

1. **Mostrar el dashboard con datos reales** → http://localhost:5001:
   > "Acá hay clases ya procesadas: claridad del instructor, satisfacción con el desglose de
   > emociones, cuánta gente asistió y si se quedó hasta el final. **Todo salió de un video,
   > automáticamente.**"

2. **El 'wow': subir un video nuevo en vivo** → ir a *Subir clase*, subir un **clip corto con
   voz**:
   > "Subo un video nuevo... esa barra de progreso es el archivo yendo **directo a S3**. Y el
   > sistema arranca el análisis solo."
   ```bash
   docker compose exec web flask aws-poll-jobs   # consultar hasta que termine (~1-3 min)
   ```
   > "En un par de minutos la clase nueva aparece con sus 5 métricas."

> Mientras procesa el clip (1-3 min), seguir mostrando las clases ya analizadas — sin silencios.

### Paso 4 — Honestidad técnica (30 s) — suma puntos
> "Al probarlo en real descubrimos que **AWS descontinuó el API que seguía personas**
> (Rekognition People Pathing, retirado el 31-oct-2025). En vez de quedarnos sin
> asistencia/permanencia, las **derivamos de la detección de caras** (cuántas caras hay al
> inicio/mitad/final del video). Además hicimos la ingesta **escalable** (guardamos un
> resumen, no el JSON gigante). O sea: el sistema **se adapta** cuando un servicio cambia."

### Paso 5 — Cierre (15 s)
> "Resumen: construimos el motor que convierte videos en analítica accionable — con **subida
> directa a S3**, **detección automática de idioma**, probado de punta a punta contra AWS
> real, código modular y **66 tests** automáticos. Es la base de todo el valor del producto."

---

## 2. Los servicios de AWS que usamos (lo importante si no cachas AWS)

AWS es un conjunto de servicios en la nube que se usan por API (con la librería `boto3`
en Python). Cada uno hace **una** cosa. Estos son los que tocamos:

| Servicio AWS | Qué es / qué hace | Para qué lo usamos |
|--------------|-------------------|--------------------|
| **S3** (Simple Storage Service) | Disco en la nube: guarda archivos ("objetos") dentro de "buckets". Cada objeto se identifica por `bucket` + `key` (la ruta). | Guardamos y leemos los videos. La app los **sube directo del navegador a S3** (URL pre-firmada). |
| **Rekognition** | Visión por computadora sobre imágenes y video. | Detección de caras + emociones. |
| → Rekognition **Face Detection** | Detecta rostros y sus **emociones** (HAPPY, SAD, CALM, etc.) y permite contar caras por frame. | Satisfacción + asistencia/permanencia (conteo de caras). |
| → Rekognition **Person Tracking** | Seguía personas individualmente. **AWS lo descontinuó (oct-2025).** | *Ya no se usa → se reemplazó por conteo de caras (Face Detection).* |
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
   Video en S3  (subido directo desde la app, o ya presente por cámaras)
        │
        ▼
  enqueue_analysis(clase)         ← se dispara el análisis de una clase
        │
        ▼
  Pipeline Orchestrator
   ├─ valida que el objeto exista en S3
   ├─ lanza Rekognition Face Detection    ┐ jobs asíncronos
   └─ lanza Transcribe                     ┘ (guardan un JobId)
        │   (Person Tracking lo descontinuó AWS; cada job queda "submitted")
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
| **Asistencia** | Rekognition Face Detection* | Pico de caras simultáneas (inicio/mitad/final del video). |
| **Permanencia** | Rekognition Face Detection* | % de personas (caras) presentes al final vs. al inicio. |
| **Claridad de instrucciones** | Transcribe | Score 0-100 según palabras/min (óptimo 120-160), largo de frases y pausas. |
| **Habla vs. demostración** | Transcribe | % del tiempo con voz vs. silencio (fusiona palabras en segmentos de habla). |
| **Satisfacción del alumno** | Rekognition Face Detection + Comprehend | 70% emociones faciales (HAPPY/SURPRISED suman, SAD/ANGRY restan) + 30% sentimiento del texto. |

> *Originalmente asistencia/permanencia usaban **Person Tracking**, pero AWS lo descontinuó
> (ver hallazgo 1). Se reemplazó por conteo de caras de **Face Detection** por tercio del
> video. El código mantiene Person Tracking como fuente primaria si algún día revive.

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
(lanzar jobs → polling → métricas → estado `completada`) y produjo **las 5 métricas con
datos reales**.

**Tres hallazgos durante la prueba** (todos típicos de integrar con AWS, y cada uno dejó el
sistema mejor):

1. **AWS descontinuó Person Tracking (People Pathing).** `StartPersonTracking` devolvía
   `AccessDenied` con mensaje vacío, **solo esa acción** (FaceDetection, LabelDetection,
   ContentModeration, SegmentDetection y las APIs base de Rekognition sí funcionaban).
   Tras descartar IAM, permission boundary, SCP (la cuenta es la *management account*, donde
   los SCP no aplican) y región, la causa real es que **AWS retiró Amazon Rekognition People
   Pathing el 31-oct-2025** — por eso bloquea esa única acción. **No es un bug nuestro.**
   **Solución implementada:** asistencia y permanencia ahora se derivan de **Face Detection**
   (conteo de caras simultáneas por tercio del video: inicio/mitad/final), reusando los jobs
   que ya corrimos (costo extra ~0). Para producción, la ruta robusta es Label Detection
   ("Person") o YOLOv9 + ByteTrack en SageMaker (lo que recomienda AWS).

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

| Clase | Duración | Asistencia | Permanencia | Claridad | Satisfacción | Habla vs. demo |
|-------|----------|-----------|-------------|----------|--------------|----------------|
| Silver Sneakers | 12 s | 5 | 66.7 % | 86 | 58 | 54.7 % |
| Mat Pilates | 45 min | 16 | 100 % | 72 | 60 | 73.4 % |
| Reformer | 57 min | 12 | 83.3 % | 78 | 54 | 65.3 % |
| Hot Pilates | 61 min | 28 | 100 % | 74 | 62 | 69.6 % |

*(Asistencia = peak de caras simultáneas; permanencia = % de caras al final vs. inicio.
Cuenta caras visibles, así que es un piso — para producción, Label Detection / YOLOv9 sería
más preciso.)*

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
- Las 16 tareas del plan implementadas, con **61/61 tests** pasando (mockeando AWS).
- Pipeline probado **en real** contra AWS: **las 5 métricas** con datos reales end-to-end,
  en las 4 clases.

**Pendiente / mejoras:**
- Asistencia/permanencia más precisas: migrar de Face Detection a **Label Detection
  ("Person")** o **YOLOv9 + ByteTrack** en SageMaker (recomendado por AWS) — capta gente de
  espaldas o en el suelo, no solo caras.
- Subir el código y abrir los Pull Requests (hoy está en ramas locales).
- Rotar las credenciales de AWS usadas en la demo (higiene de seguridad).

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
