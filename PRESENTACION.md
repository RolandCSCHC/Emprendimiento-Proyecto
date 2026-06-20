# GymSight — Presentación del estudio

> Análisis automático de clases grupales (yoga / fitness) a partir de **video y audio**,
> para entregar a cada profesor métricas objetivas y recomendaciones accionables
> **sin encuestas ni interrumpir la clase**.

> Nota: los campos marcados con `[COMPLETAR]` son datos del equipo/estudio de mercado que
> deben llenar ustedes; el resto son resultados reales del piloto técnico ya ejecutado.

---

## 1. Detalles del estudio realizado

**¿Qué?**
Piloto técnico para validar una pregunta central: *¿es posible medir de forma objetiva la
calidad de una clase grupal (asistencia, permanencia, claridad, dinámica habla/demostración
y satisfacción) usando solo el video y el audio de la clase, sin encuestas?* Y, a partir de
eso, *¿se pueden generar recomendaciones útiles para que el profesor mejore?*

**¿Quiénes?**
- Equipo: `[COMPLETAR: integrantes]`.
- Caso piloto analizado: clases del perfil de profesora **"Malakita Yoga"** (grabaciones
  reales de clases grupales de yoga/pilates).
- Estudio de problema/clientes (entrevistas a profesores y gimnasios): `[COMPLETAR: a quiénes
  entrevistaron, cuántos, qué dolor reportaron]`.

**¿Cuántos?**
- **4 sesiones reales** procesadas de punta a punta por el pipeline de IA (caso Malakita).
- **8 jobs de AWS** ejecutados con éxito (Rekognition FaceDetection + Transcribe por sesión).
- **20 métricas** calculadas para el caso piloto (5 métricas × 4 sesiones).
- Plataforma de demostración cargada con `[14 sesiones / 70 métricas en total, incluyendo
  datos de ejemplo]` para mostrar el dashboard lleno.

**¿Dónde?**
- Grabaciones de clases grupales de yoga/pilates.
- Procesamiento en la nube: **AWS región us-west-2** (Rekognition, Transcribe, Comprehend,
  Bedrock). App ejecutándose localmente vía Docker.

**¿Cómo?**
1. Se suben las grabaciones de cada sesión (el video va directo a S3 con URLs pre-firmadas).
2. El pipeline lanza automáticamente: **Rekognition FaceDetection** (caras/emociones) y
   **Amazon Transcribe** (transcripción con timestamps).
3. Al terminar, se calculan las 5 métricas y se aplica **Amazon Comprehend** (sentimiento).
4. **Amazon Bedrock (modelo Amazon Nova)** genera 3–5 recomendaciones en lenguaje natural a
   partir del historial de métricas del profesor.

---

## 2. Evidencia

**Logs de procesamiento real en AWS** (jobs completados, caso Malakita):

| Fecha sesión | Servicio AWS | Estado | Job ID (AWS) |
|---|---|---|---|
| 15/06 | Rekognition FaceDetection | completed | `bc5de59b920f87ba70fb7a982f3f…` |
| 15/06 | Transcribe | completed | `gymsight-d04b7ff0-da52-4050-…` |
| 16/06 | Rekognition FaceDetection | completed | `5ed46c4bce057f7266670aeffb1b…` |
| 16/06 | Transcribe | completed | `gymsight-dee077c4-469c-4eb5-…` |
| 19/06 | Rekognition FaceDetection | completed | `e4b1767797350f732f1581cb105b…` |
| 19/06 | Transcribe | completed | `gymsight-54d0d924-9131-440d-…` |
| 20/06 | Rekognition FaceDetection | completed | `71c80a083090fb496c8560a8b721…` |
| 20/06 | Transcribe | completed | `gymsight-014c40b2-0806-43db-…` |

**Desglose interno de una sesión** (16/06) — demuestra que las métricas se derivan de datos
medibles, no son valores arbitrarios:

- **Claridad = 73/100** → palabras/min: **79.6**, longitud media de frase: **20.2 palabras**,
  pausas/min: **3.9** (rango óptimo WPM: 120–160).
- **Tiempo hablando = 57.5%** → **1382.6 s hablando** vs **1024 s en silencio** sobre
  **2406.6 s** totales (~40 min de clase).
- **Satisfacción = 61/100** → score visual 51.2 (emociones: CALM 70%, SURPRISED 7%, HAPPY 4.5%,
  SAD 7.6%) ponderado 70% + score textual 82.5 ponderado 30%.

**Capturas a incluir en la presentación** (`[COMPLETAR: pegar screenshots]`):
- Dashboard con la lista de clases.
- Detalle de "Yoga Malakita": gráficos de evolución de las 5 métricas.
- Sección de recomendaciones IA generadas para la profesora.

---

## 3. Variables medidas

Cinco métricas por sesión, cada una con una fórmula explícita (código en
`app/services/analysis/metrics_extractor.py`):

| Variable | Qué mide | Fuente | Cálculo | Unidad |
|---|---|---|---|---|
| **Asistencia** | Cuántas personas asisten | Rekognition FaceDetection | Peak de caras simultáneas (inicio/mitad/final) | personas |
| **Permanencia** | Si se quedan hasta el final | Rekognition FaceDetection | Caras al final ÷ caras al inicio × 100 | % |
| **Claridad de instrucciones** | Qué tan claras son las indicaciones | Transcribe | 0.5·WPM(120–160) + 0.25·largo_frase(8–15) + 0.25·pausas/min(2–8) | score 0–100 |
| **Tiempo hablando vs. demostrando** | Cuánto habla vs. demuestra | Transcribe | Segundos con voz ÷ duración total × 100 | % hablando |
| **Satisfacción del alumno** | Clima emocional de la clase | Rekognition + Comprehend | 70% emociones faciales + 30% sentimiento del texto | score 0–100 |

Todas se obtienen **automáticamente desde el video/audio**, sin preguntar nada a los alumnos.

---

## 4. Resultados encontrados

**Métricas reales del caso piloto (Malakita Yoga, 4 sesiones):**

| Fecha | Asistencia | Permanencia | Claridad | % Hablando | Satisfacción |
|---|---|---|---|---|---|
| 15/06 | 10 | 90% | 68 | 34.2% | 61 |
| 16/06 | 9 | 100% | 73 | 57.5% | 61 |
| 19/06 | 18 | 100% | 61 | 33.2% | 60 |
| 20/06 | 7 | 100% | 67 | 36.4% | 52 |

**Hallazgos:**
- El sistema produce métricas **coherentes y trazables** (cada valor tiene su desglose).
- Se observan **patrones accionables**: por ejemplo, la sesión con más tiempo hablando (57.5%)
  coincide con la métrica de claridad más alta, mientras que la asistencia es variable entre
  sesiones (7 a 18) — justo el tipo de señal que un profesor no tiene hoy sin encuestas.
- Las **recomendaciones de IA** salen específicas y aplicables. Ejemplo real generado:
  > *"Reducir el tiempo hablando: demuestra los movimientos en vez de describirlos; ejecuta
  > junto a los alumnos y usa señales corporales y conteo en lugar de explicaciones largas."*
- **Robustez ante limitaciones de AWS:** Rekognition People Pathing está restringido a nivel
  de cuenta; el sistema cae automáticamente a FaceDetection y **igual entrega las 5 métricas**.

---

## 5. Conclusiones

1. **Es viable** extraer métricas objetivas de calidad de clase desde video/audio, sin encuestas.
2. Las métricas son **explicables** (no caja negra): cada número se puede auditar con su detalle.
3. La capa de IA generativa convierte datos en **consejos concretos** que el profesor puede
   aplicar en su próxima clase, que es lo que realmente genera valor.
4. La arquitectura **degrada con elegancia** ante restricciones de servicios externos.
5. El pipeline funciona **de punta a punta contra AWS real**, no es un mockup.

---

## 6. ¿La solución actual resuelve el dolor? ¿Qué cambios faltan?

**El dolor:** profesores y gimnasios no tienen feedback objetivo sobre la calidad de las clases;
dependen de encuestas (baja respuesta, sesgo, intrusivas) o de la percepción del profesor.

**¿Lo resuelve?** **Parcialmente, y la dirección está validada.** Hoy ya entrega métricas y
recomendaciones reales sin encuestas. Para que sea un producto robusto faltan:

- **Asistencia/permanencia más precisas:** reemplazar el conteo de caras por detección/tracking
  de personas (Label Detection "Person" o YOLOv9 + ByteTrack en SageMaker). Las caras se pierden
  si el alumno se gira o está de espaldas.
- **Validación contra terreno real (ground truth):** comparar las métricas con asistencia/
  satisfacción reales para confirmar que miden lo que dicen medir.
- **Captura en gimnasios reales:** definir setup de cámara/micrófono, consentimiento y privacidad.
- **Operación a escala:** automatizar el polling (hoy manual) con EventBridge/SNS, costos por hora
  de video, y panel multi-gimnasio.
- **Cierre del loop:** medir si seguir las recomendaciones efectivamente mejora las métricas.

---

## 7. Principales incertidumbres que aún quedan

- **Validez de las métricas:** ¿correlacionan con resultados reales (retención, satisfacción,
  renovación de membresías)? Es la incertidumbre #1.
- **Generalización:** ¿funcionan los mismos umbrales para yoga, spinning, funcional, etc.?
- **Condiciones reales de grabación:** iluminación, ángulo, ruido, clases llenas (oclusión de caras).
- **Privacidad y consentimiento:** grabar alumnos implica marco legal y aceptación del gimnasio.
- **Disposición a pagar:** ¿cuánto vale esto para un gimnasio/profesor y cuál es el modelo de negocio?
- **Costo unitario:** procesar video en la nube tiene costo por minuto; ¿se sostiene a escala?
- **Adopción del profesor:** ¿confía en las recomendaciones de IA y cambia su forma de enseñar?

---

*Demo técnica: ver `README.md` para levantar la app y `gymsight_demo.sql` para restaurar los
datos del piloto.*
