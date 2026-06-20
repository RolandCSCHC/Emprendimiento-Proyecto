# Guía rápida — Levantar la demo con los datos nuevos

Pasos para dejar la app igual a como está hoy: con la profesora **Malakita Yoga**
(4 sesiones analizadas), los **gráficos históricos** y los **tips de IA** (Amazon Bedrock / Nova).

> Requisito: tener Docker y **acceso a AWS** (S3, Rekognition, Transcribe, Comprehend y
> Bedrock con el modelo **Nova habilitado** en `us-west-2`). Todo el equipo ya tiene acceso.

## 1. Traer el código

```bash
git checkout main
git pull
```

## 2. Configurar el `.env`

```bash
cp .env.example .env
```

Editar `.env` y dejar (con credenciales propias):

```
AWS_ENABLED=true
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=...tu access key...
AWS_SECRET_ACCESS_KEY=...tu secret...
S3_BUCKET=rekognition-gym-videos
```

> El `.env` está en `.gitignore`: nunca se sube. Cada quien pone sus credenciales.

## 3. Construir y levantar

```bash
docker compose up -d --build
```

## 4. Cargar el dump (Malakita + toda la data)

```bash
./docker/restore-demo.sh gymsight_demo.sql
```

Esto recrea la base, restaura el dump y deja la app en **http://localhost:5001**.

## 5. Ver las cosas nuevas

- Dashboard → **Yoga Malakita**.
- Arriba: **gráficos de evolución** de las 5 métricas (4 sesiones).
- Abajo: sección **"Recomendaciones para Malakita Yoga"** con los tips de IA.

---

## Qué necesita AWS y qué no

| | Sin AWS (`AWS_ENABLED=false`) | Con AWS |
|---|---|---|
| Gráficos / data histórica | ✅ (vienen en el dump) | ✅ |
| Tips de IA | ❌ no aparece la sección | ✅ se generan en vivo |
| Subir y procesar videos nuevos | ❌ | ✅ |

Para grabar el video mostrando los **tips**, hay que tener `AWS_ENABLED=true`.

## Tips de operación

- Si cambias el `.env` con la app ya arriba, recarga las variables recreando el contenedor:
  ```bash
  docker compose up -d --force-recreate web
  ```
- Si subes videos nuevos, después corre el poller para traer los resultados de AWS:
  ```bash
  docker compose exec web flask aws-poll-jobs
  ```
- Para tips con más calidad, en el `.env`:
  ```
  BEDROCK_MODEL_ID=us.amazon.nova-pro-v1:0
  ```

## Si algo no aparece

- **No sale la sección de tips:** el `.env` quedó en `AWS_ENABLED=false` o no recreaste el
  contenedor. Corre `docker compose up -d --force-recreate web`.
- **La sección de tips da error:** falta acceso a Bedrock o el modelo Nova no está habilitado
  en la cuenta/región.
- **No hay gráficos:** revisa que el dump se haya restaurado (paso 4).
