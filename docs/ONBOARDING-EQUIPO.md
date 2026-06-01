# Onboarding — probar el pipeline AWS de Gymsight

Guía para que un compañero del equipo levante la app y pruebe el análisis con AWS
**de punta a punta**, sin conocer el proyecto por dentro.

---

## 0. Qué vas a probar

Gymsight toma videos de clases (ya guardados en **S3**) y genera **5 métricas** con IA de
AWS (Rekognition, Transcribe, Comprehend): asistencia, permanencia, claridad, habla vs.
demostración y satisfacción. Vas a levantar la app, disparar el análisis de las clases de
demo y ver los resultados en el dashboard.

---

## 1. Requisitos

- **Docker Desktop** instalado y corriendo.
- **Tus credenciales AWS** (te las pasa Camila en privado): un `AWS_ACCESS_KEY_ID` y un
  `AWS_SECRET_ACCESS_KEY` de tu usuario IAM (estás en el grupo `gymsight-devs`).

> Tu usuario solo tiene permisos para este proyecto (S3 del bucket + Rekognition +
> Transcribe + Comprehend). No puedes tocar nada más de la cuenta AWS.

---

## 2. Bajar el código

```bash
git clone https://github.com/RolandCSCHC/Emprendimiento-Proyecto.git
cd Emprendimiento-Proyecto
# (todo está en main)
```

---

## 3. Configurar el `.env`

```bash
cp .env.example .env
```

Edita `.env` y déjalo así (las dos primeras llaves son **las tuyas**, el resto es fijo):

```
AWS_ENABLED=true
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=<tu access key>
AWS_SECRET_ACCESS_KEY=<tu secret>
S3_BUCKET=rekognition-gym-videos
TRANSCRIBE_LANGUAGE_CODE=auto
SECRET_KEY=cualquier-cosa-local
```

> `TRANSCRIBE_LANGUAGE_CODE=auto` detecta el idioma solo (es/en). El resto del bloque es fijo.

> ⚠️ Nunca subas tu `.env` a git (ya está en `.gitignore`). Tus credenciales son personales.

---

## 4. Levantar la app

```bash
docker compose up --build
```

La primera vez tarda unos minutos (descarga imágenes, instala dependencias). Esto además
**crea la base de datos y siembra 4 clases de demo** ya enlazadas a videos reales en S3.

Cuando veas el log de `gunicorn` corriendo, abre: **http://localhost:5001**

> Si el puerto `5433` (Postgres) está ocupado en tu equipo, edita `docker-compose.yml` y
> cambia `5433:5432` por otro puerto, ej. `5434:5432`.

---

## ⚡ Atajo para demo: cargar datos YA analizados (sin gastar en AWS)

Si solo quieres **mostrar el dashboard con métricas reales** (sin esperar ni pagar análisis),
restaura el dump incluido en el repo (`gymsight_demo.sql`) — trae **6 clases ya analizadas**:

```bash
docker compose up -d db                                                    # solo la base de datos
sleep 5
docker compose exec -T db psql -U gymsight -d gymsight < gymsight_demo.sql # restaurar el dump
docker compose up -d web                                                   # levantar la app
# → http://localhost:5001 : 6 clases con sus 5 métricas, al instante
```

No llama a AWS ni cuesta nada. Para el "wow" en vivo, igual puedes **subir un clip corto**
(1-3 min de proceso) — ver el paso siguiente.

> Necesitas las credenciales del `.env` (paso 3) **solo** si vas a subir/analizar videos
> nuevos. Para ver la demo restaurada, ni eso hace falta.

---

## 5. Disparar el análisis 🎬

En otra terminal (con la app corriendo):

```bash
# Lanza el análisis de las 4 clases de demo
docker compose exec web flask aws-analyze

# Consulta el estado de los jobs y calcula métricas cuando terminan.
# Repetir cada 1-2 min hasta que las clases queden "completada".
docker compose exec web flask aws-poll-jobs
```

Los videos largos (1 h) tardan **20-35 min** en FaceDetection. El corto (Silver Sneakers,
15 s) termina en **~1 min**.

Cuando una clase está lista, ábrela en el dashboard y verás las 5 métricas con sus valores.

---

## 6. ⚠️ Cuidado con los costos

Rekognition y Transcribe **cuestan dinero por uso** (no es gratis como levantar la app):

- **Empieza por la clase "Silver Sneakers" (15 s)** — cuesta centavos.
- Los videos de 1 h cuestan varios dólares **cada vez** que los procesas.
- **No relances el análisis en bucle** de los videos grandes.

Si quieres analizar solo una clase, saca su id y úsalo:
```bash
docker compose exec web flask aws-analyze <clase_id>
```

---

## 7. Comandos útiles

```bash
docker compose ps                      # estado de los contenedores
docker compose logs -f web             # ver logs de la app
docker compose down                    # apagar (los datos quedan guardados)
docker compose down -v                 # apagar y BORRAR datos (empezar de cero)
docker compose exec web flask aws-poll-jobs   # volver a consultar jobs
```

---

## 8. Si algo falla

| Síntoma | Causa probable / solución |
|---------|---------------------------|
| `AccessDenied` al analizar | Credenciales mal pegadas en `.env`, o `AWS_ENABLED` no es `true`. |
| `AccessDenied` solo en *PersonTracking* | Normal: AWS descontinuó ese API; asistencia/permanencia salen de FaceDetection. |
| Error **403 / CORS** al subir el video | Entra por **`http://localhost:5001`** (no `127.0.0.1`). La subida es directa a S3 y el bucket tiene CORS solo para ese origen. |
| Puerto 5433 ocupado | Cambia el puerto del `db` en `docker-compose.yml`. |
| La clase queda en "analizando" | Los jobs aún corren; vuelve a correr `flask aws-poll-jobs` en unos minutos. |
| El dashboard muestra métricas vacías | El análisis aún no termina, o no corriste `aws-analyze`. |

---

## 9. Más contexto

- `README.md` — visión general del proyecto.
- `docs/PRESENTACION-AWS.md` — cómo funciona el pipeline (para presentar).
- `docs/AVANCES-AWS.md` — bitácora técnica.
- `docs/DEPLOY.md` — qué cambia para producción.

¿Dudas? Pregúntale a Camila. 🙌
