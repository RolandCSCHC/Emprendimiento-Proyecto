# Deploy — cosas a configurar (Local vs Producción)

Guía de qué cambia al llevar Gymsight de local a un entorno desplegado.
**Principio clave:** el código es **agnóstico al entorno** — todo se controla por
**variables de entorno** y por el **rol IAM**. No hay que reescribir lógica para deploy.

---

## 1. Lo más importante: credenciales AWS (rol IAM, no keys) 🔑

| | Local | Producción |
|---|-------|------------|
| Autenticación AWS | `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` en `.env` | **Rol IAM** pegado al cómputo (EC2 instance profile / ECS task role / Lambda role) — **sin keys** |

- En producción **NO** se ponen access keys. Se asigna un **rol IAM** al contenedor/instancia
  y AWS entrega credenciales temporales automáticas.
- El código ya lo soporta: `app/services/aws/boto_session.py` usa las keys **solo si existen**;
  si no, cae en la cadena de credenciales por defecto (el rol IAM). → En deploy, **dejar
  `AWS_ACCESS_KEY_ID` y `AWS_SECRET_ACCESS_KEY` vacías** y adjuntar el rol.

### Permisos que necesita el rol IAM
- `s3:GetObject`, `s3:PutObject` (subir y leer videos en el bucket)
- `rekognition:StartFaceDetection`, `rekognition:GetFaceDetection` (y demás `rekognition:*` que uses)
- `transcribe:StartTranscriptionJob`, `transcribe:GetTranscriptionJob`
- `comprehend:DetectSentiment`
- Si usas webhook SNS: un rol que Rekognition pueda asumir para publicar en el topic
  (`REKOGNITION_SNS_ROLE_ARN`).

---

## 2. Variables de entorno

| Variable | Local | Producción |
|----------|-------|------------|
| `AWS_ENABLED` | `true` para probar AWS | `true` |
| `AWS_REGION` | `us-west-2` (demo) | región real |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | tus keys | **vacías** (rol IAM) |
| `S3_BUCKET` | bucket demo | bucket real |
| `DATABASE_URL` | Postgres de Docker (`db:5432`) | **RDS** u otra base gestionada |
| `SECRET_KEY` | valor dev | **secreto real, largo y único** |
| `FLASK_ENV` | `development` | `production` (ya configurado en `docker-compose`) |
| `TRANSCRIBE_LANGUAGE_CODE` | `en-US` | idioma real del audio |
| `SNS_TOPIC_ARN` / `REKOGNITION_SNS_ROLE_ARN` | — | solo si usas webhook SNS |
| `MAX_UPLOAD_MB` | 800 | según tamaño de videos |

> **Mejor práctica:** en producción, guardar los secretos en **AWS Secrets Manager** o
> **SSM Parameter Store** en vez de un archivo `.env`.

---

## 3. Base de datos

- Local: Postgres del `docker-compose`.
- Deploy: una base gestionada (**RDS Postgres**). Solo cambia `DATABASE_URL`.
- **Ojo con el seed de demo:** el `docker/entrypoint.sh` corre `flask init-db`, que crea las
  tablas **y siembra 4 clases de demo**. En producción **no** quieres esos datos de demo:
  - Cambiar el entrypoint para usar **migraciones** (`flask db upgrade`) en vez de
    `init-db`, o
  - Quitar el seed (el `seed_database` solo siembra si la base está vacía, pero igual conviene
    no llamarlo en prod).

---

## 4. Detección de jobs terminados: polling vs webhook

Los jobs de Rekognition/Transcribe son asíncronos. Dos formas de cerrarlos:

| | Local | Producción |
|---|-------|------------|
| **Polling** | `flask aws-poll-jobs` manual | Programado: cron, **EventBridge** o tarea ECS cada 1-5 min |
| **Webhook SNS** | No (no hay URL pública) | `POST /webhooks/aws/sns` con URL pública HTTPS + `SNS_TOPIC_ARN` + `REKOGNITION_SNS_ROLE_ARN`. Endpoint ya implementado con validación de firma. |

Con webhook tienes menor latencia; con polling es más simple. Puedes usar ambos.

---

## 5. Subida de videos

- La subida por la app va **server-side a S3** (boto3) cuando `AWS_ENABLED=true`.
- Detrás de un proxy (**nginx / ALB**) hay que **subir el límite de tamaño del body**
  (`client_max_body_size` en nginx) y `MAX_UPLOAD_MB`, porque los videos son grandes.
- Timeout de gunicorn ya está en 120s; videos muy grandes pueden requerir más.
- **Mejora futura (escalabilidad):** subida directa del navegador a S3 con **presigned URL**
  (el archivo no pasa por el servidor). Hoy es server-side, suficiente para empezar.

---

## 6. Otros

- **HTTPS/TLS:** terminar TLS en el ALB / proxy (necesario para el webhook SNS y para subir).
- **Workers de gunicorn:** ajustar `-w` según CPU.
- **Almacenamiento de `raw_response`:** ya es compacto (resúmenes), no crece con la duración
  del video — no hay riesgo del límite de 256 MB de JSONB.

---

## Checklist de deploy

- [ ] Rol IAM con permisos S3 + Rekognition + Transcribe + Comprehend, adjuntado al cómputo.
- [ ] `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` **vacías** (usar rol).
- [ ] `DATABASE_URL` apuntando a RDS.
- [ ] `SECRET_KEY` real (Secrets Manager / SSM).
- [ ] `S3_BUCKET`, `AWS_REGION`, `TRANSCRIBE_LANGUAGE_CODE` reales.
- [ ] Entrypoint sin seed de demo (usar `flask db upgrade`).
- [ ] Polling programado (cron/EventBridge) **o** webhook SNS configurado.
- [ ] Límite de body del proxy + `MAX_UPLOAD_MB` acordes al tamaño de videos.
- [ ] HTTPS/TLS configurado.
