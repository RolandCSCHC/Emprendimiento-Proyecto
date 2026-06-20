# Requirements Document

## Introduction

Esta funcionalidad agrega a GymSight la capacidad de generar recomendaciones personalizadas en lenguaje natural para cada profesor, basándose en su historial de métricas de rendimiento a través de múltiples sesiones de clase. Se utiliza AWS Bedrock como motor de generación de texto. Las recomendaciones se muestran como una sección de "tips" en la interfaz, complementando los gráficos de evolución ya existentes en la vista de detalle de programa.

## Glossary

- **Sistema_Recomendaciones**: Módulo del backend encargado de recopilar datos históricos de métricas de un profesor, construir el prompt y llamar a AWS Bedrock para generar recomendaciones.
- **Bedrock_Client**: Componente que encapsula la comunicación con el servicio AWS Bedrock (InvokeModel API).
- **Profesor**: Entidad existente en la base de datos que imparte clases en un gimnasio.
- **Programa**: Clase recurrente (ProgramaClase) que agrupa sesiones semanales impartidas por un profesor.
- **Sesión**: Instancia individual de una clase (modelo Clase) con métricas asociadas.
- **Métricas**: Valores numéricos extraídos del análisis AWS (asistencia, permanencia, claridad_instrucciones, tiempo_hablando_vs_demostrando, satisfaccion_alumno).
- **Recomendación**: Texto en lenguaje natural generado por AWS Bedrock con consejos específicos para que el profesor mejore sus clases.
- **Vista_Programa**: Página web que muestra el detalle de un programa, incluyendo gráficos de evolución y la nueva sección de recomendaciones.

## Requirements

### Requirement 1: Agregación de datos históricos del profesor

**User Story:** Como administrador del gimnasio, quiero que el sistema consolide las métricas de todas las sesiones analizadas de un profesor, para que las recomendaciones se basen en todo su historial y no solo en una sesión individual.

#### Acceptance Criteria

1. WHEN a recommendation is requested for a professor, THE Sistema_Recomendaciones SHALL collect metrics from all sessions with status "completada" or "completada_parcial" across all programs belonging to that professor.
2. THE Sistema_Recomendaciones SHALL include the five metric types (asistencia, permanencia, claridad_instrucciones, tiempo_hablando_vs_demostrando, satisfaccion_alumno) for each session in the aggregated data.
3. WHEN a professor has fewer than 2 completed sessions, THE Sistema_Recomendaciones SHALL return an indication that insufficient data is available instead of generating recommendations.
4. THE Sistema_Recomendaciones SHALL compute summary statistics (average, minimum, maximum, and trend direction) for each metric type across the collected sessions.

### Requirement 2: Generación de recomendaciones con AWS Bedrock

**User Story:** Como administrador del gimnasio, quiero que un modelo de IA genere consejos personalizados basados en los datos históricos de un profesor, para que el profesor reciba orientación útil y específica para mejorar.

#### Acceptance Criteria

1. THE Bedrock_Client SHALL invoke the AWS Bedrock InvokeModel API using the model configured in the application settings.
2. WHEN the aggregated metrics are available, THE Sistema_Recomendaciones SHALL construct a prompt that includes the summary statistics, trends, and session count for the professor.
3. THE Sistema_Recomendaciones SHALL instruct the model to produce recommendations in Spanish.
4. THE Sistema_Recomendaciones SHALL request between 3 and 5 concrete, actionable recommendations from the model.
5. WHEN the Bedrock API call succeeds, THE Sistema_Recomendaciones SHALL parse the model response and return a structured list of recommendations.
6. IF the Bedrock API call fails, THEN THE Sistema_Recomendaciones SHALL return a user-friendly error message and log the error details.

### Requirement 3: Integración del cliente AWS Bedrock

**User Story:** Como desarrollador, quiero un cliente Bedrock que siga los mismos patrones de configuración que los demás servicios AWS del proyecto, para mantener la consistencia arquitectónica.

#### Acceptance Criteria

1. THE Bedrock_Client SHALL use the existing `get_boto_client` helper from `app/services/aws/boto_session.py` to obtain a configured boto3 client for the service "bedrock-runtime".
2. THE Bedrock_Client SHALL read the model identifier from the application configuration key `BEDROCK_MODEL_ID`.
3. WHILE the configuration key `AWS_ENABLED` is set to false, THE Bedrock_Client SHALL not attempt any API call and SHALL return a graceful degradation response.
4. IF the `BEDROCK_MODEL_ID` configuration is missing, THEN THE Bedrock_Client SHALL raise a descriptive configuration error.

### Requirement 4: Endpoint API para recomendaciones

**User Story:** Como desarrollador del frontend, quiero un endpoint que devuelva las recomendaciones generadas para un profesor específico, para poder mostrarlas de forma asíncrona en la interfaz.

#### Acceptance Criteria

1. THE Sistema_Recomendaciones SHALL expose an HTTP GET endpoint at `/api/profesores/<profesor_id>/recomendaciones`.
2. WHEN the endpoint is called with a valid profesor_id, THE Sistema_Recomendaciones SHALL return a JSON response containing the list of recommendations.
3. IF the profesor_id does not correspond to an existing professor, THEN THE Sistema_Recomendaciones SHALL return HTTP status 404 with an error message.
4. WHEN the professor has insufficient data (fewer than 2 sessions), THE Sistema_Recomendaciones SHALL return HTTP status 200 with an empty recommendations list and a message indicating insufficient data.
5. IF an internal error occurs during generation, THEN THE Sistema_Recomendaciones SHALL return HTTP status 503 with a descriptive error message.

### Requirement 5: Visualización de recomendaciones en la interfaz

**User Story:** Como administrador del gimnasio, quiero ver una sección de recomendaciones en la página de detalle de programa, para que pueda revisar los consejos de mejora junto con los gráficos existentes.

#### Acceptance Criteria

1. THE Vista_Programa SHALL display a "Recomendaciones IA" section below the charts section on the programa detail page.
2. WHEN the page loads, THE Vista_Programa SHALL make an asynchronous request to the recommendations endpoint for the professor associated with the current program.
3. WHILE the recommendations are loading, THE Vista_Programa SHALL display a loading indicator in the recommendations section.
4. WHEN recommendations are received successfully, THE Vista_Programa SHALL render each recommendation as a distinct card or list item with readable formatting.
5. WHEN the API returns an insufficient data message, THE Vista_Programa SHALL display a helpful message indicating that more analyzed sessions are needed.
6. IF the API returns an error, THEN THE Vista_Programa SHALL display an error message informing the user that recommendations could not be generated at this time.

### Requirement 6: Configuración y degradación elegante

**User Story:** Como desarrollador de operaciones, quiero que la funcionalidad de recomendaciones sea configurable y falle de forma elegante, para que la aplicación siga funcionando normalmente cuando Bedrock no esté disponible.

#### Acceptance Criteria

1. THE Sistema_Recomendaciones SHALL read the following configuration values: `AWS_ENABLED`, `BEDROCK_MODEL_ID`, and `BEDROCK_MAX_TOKENS`.
2. WHILE `AWS_ENABLED` is set to false, THE Vista_Programa SHALL hide the recommendations section entirely.
3. THE Sistema_Recomendaciones SHALL use a default value of 1024 for `BEDROCK_MAX_TOKENS` when the configuration key is not provided.
4. IF AWS credentials are invalid or expired, THEN THE Sistema_Recomendaciones SHALL log a warning and return a degradation response without crashing the application.
