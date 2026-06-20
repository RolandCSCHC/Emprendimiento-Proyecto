# Implementation Plan: AI Teacher Recommendations

## Overview

Implementar el módulo de recomendaciones inteligentes para profesores usando AWS Bedrock. El plan sigue un enfoque incremental: primero la configuración, luego el cliente Bedrock, el servicio de recomendaciones con su lógica pura, el endpoint API, y finalmente la integración frontend. Los tests de propiedad validan la lógica pura (filtrado, estadísticas, prompt, parsing) y se ubican cerca de su implementación correspondiente.

## Tasks

- [ ] 1. Add Bedrock configuration and dependencies
  - [ ] 1.1 Add configuration keys to `app/config.py`
    - Add `BEDROCK_MODEL_ID` with default `"anthropic.claude-3-haiku-20240307-v1:0"`
    - Add `BEDROCK_MAX_TOKENS` with default `1024`
    - Ensure `TestingConfig` keeps `AWS_ENABLED = False`
    - _Requirements: 6.1, 6.3_

  - [ ] 1.2 Add `hypothesis` to `requirements.txt`
    - Add `hypothesis>=6.100` to the test dependencies section
    - _Requirements: Testing infrastructure_

- [ ] 2. Implement AWS Bedrock client
  - [ ] 2.1 Create `app/services/aws/bedrock_client.py`
    - Define `ConfigurationError` and `BedrockInvocationError` custom exceptions
    - Implement `invoke_model(prompt, max_tokens)` function
    - Use `get_boto_client("bedrock-runtime")` following existing pattern in `comprehend_client.py`
    - Return empty string when `AWS_ENABLED` is False (graceful degradation)
    - Raise `ConfigurationError` when `BEDROCK_MODEL_ID` is missing
    - Handle boto3 credential and network errors, wrap in `BedrockInvocationError`
    - Add appropriate logging (WARNING for disabled AWS, ERROR for failures)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 6.4_

  - [ ]* 2.2 Write unit tests for Bedrock client in `tests/test_bedrock_client.py`
    - Test graceful degradation when `AWS_ENABLED=False`
    - Test `ConfigurationError` raised when `BEDROCK_MODEL_ID` missing
    - Test successful invocation with mocked boto3 response
    - Test `BedrockInvocationError` raised on API failure
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [ ] 3. Implement recommendation service - data aggregation
  - [ ] 3.1 Create `app/services/recommendation_service.py` with data models and aggregation
    - Define `MetricSummary` dataclass (metric_key, average, minimum, maximum, trend, session_count)
    - Define `RecommendationResult` dataclass (recommendations, status, message)
    - Implement `aggregate_professor_metrics(profesor_id)` function
    - Query sessions with status "completada" or "completada_parcial" from all programs of the professor
    - Collect all five metric types from each session's `Metrica` records
    - Return `None` if fewer than 2 completed sessions found
    - Compute summary statistics (average, minimum, maximum) per metric
    - Compute trend direction by comparing first-half vs second-half averages
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [ ]* 3.2 Write property test: Session filtering correctness
    - **Property 1: Session filtering correctness**
    - **Validates: Requirements 1.1**
    - Use Hypothesis to generate sessions with varying statuses and professor assignments
    - Assert only sessions with status "completada" or "completada_parcial" belonging to the professor are included

  - [ ]* 3.3 Write property test: Statistics computation correctness
    - **Property 2: Statistics computation correctness**
    - **Validates: Requirements 1.4**
    - Use Hypothesis to generate lists of numeric metric values
    - Assert average equals arithmetic mean, minimum equals smallest value, maximum equals largest value
    - Assert trend is consistent with first-half vs second-half comparison

- [ ] 4. Implement recommendation service - prompt building and parsing
  - [ ] 4.1 Implement `build_prompt(summaries, profesor_nombre)` function
    - Construct structured prompt including professor name, session count, and all metric summaries
    - Include instruction for 3-5 recommendations in Spanish with numbered format
    - Include all metric averages, minimums, maximums, and trend directions
    - _Requirements: 2.2, 2.3, 2.4_

  - [ ]* 4.2 Write property test: Prompt includes all metric summaries
    - **Property 3: Prompt includes all metric summaries**
    - **Validates: Requirements 2.2**
    - Use Hypothesis to generate valid MetricSummary lists and professor names
    - Assert the generated prompt contains average, min, max, trend for every metric
    - Assert prompt contains professor name and session count

  - [ ] 4.3 Implement `parse_recommendations(model_response)` function
    - Parse numbered recommendations from model response text (e.g., "1. ...\n2. ...")
    - Handle variations: bullets, dashes, numbered with/without dots
    - Return list of stripped recommendation strings without numbering prefix
    - _Requirements: 2.5_

  - [ ]* 4.4 Write property test: Recommendation parsing extracts individual items
    - **Property 4: Recommendation parsing extracts individual items**
    - **Validates: Requirements 2.5**
    - Use Hypothesis to generate texts with N numbered recommendations
    - Assert returned list has exactly N non-empty strings without numbering prefix

  - [ ] 4.5 Implement `generate_recommendations(profesor_id)` function
    - Orchestrate full flow: aggregate → build prompt → invoke model → parse
    - Return `RecommendationResult` with appropriate status for each outcome
    - Handle insufficient data case (status="insufficient_data")
    - Handle Bedrock errors gracefully (status="error")
    - Log INFO on success with recommendation count
    - _Requirements: 2.1, 2.5, 2.6_

- [ ] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Implement API endpoint
  - [ ] 6.1 Create `app/routes/api.py` with API blueprint
    - Define `api_bp = Blueprint("api", __name__, url_prefix="/api")`
    - Implement `GET /api/profesores/<profesor_id>/recomendaciones` route
    - Validate professor exists, return 404 if not found
    - Call `generate_recommendations(profesor_id)` and return JSON response
    - Return 200 with recommendations list and status on success
    - Return 200 with empty list and message for insufficient data
    - Return 503 on internal errors with descriptive message
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [ ] 6.2 Register API blueprint in `app/routes/__init__.py`
    - Import `api_bp` from `app.routes.api`
    - Add `flask_app.register_blueprint(api_bp)` to `register_blueprints`
    - _Requirements: 4.1_

  - [ ]* 6.3 Write integration tests for API endpoint in `tests/test_api_recommendations.py`
    - Test 200 response with successful recommendations (mocked Bedrock)
    - Test 200 response with insufficient data message
    - Test 404 for non-existent professor
    - Test 503 for internal service error
    - _Requirements: 4.2, 4.3, 4.4, 4.5_

- [ ] 7. Implement frontend integration
  - [ ] 7.1 Create `app/static/js/recommendations.js`
    - Implement `loadRecommendations(profesorId, container)` async function
    - Fetch from `/api/profesores/<id>/recomendaciones`
    - Show loading spinner during fetch
    - Render recommendation cards on success
    - Display "insufficient data" message when status is "insufficient_data"
    - Display error message on fetch failure or 503 response
    - _Requirements: 5.2, 5.3, 5.4, 5.5, 5.6_

  - [ ] 7.2 Modify `app/templates/programa_detail.html` to add recommendations section
    - Add `<section id="recomendaciones-section">` after the charts section
    - Include container with `id="recomendaciones-container"`
    - Add `data-profesor-id="{{ programa.profesor.id }}"` attribute
    - Add `data-aws-enabled="{{ config.AWS_ENABLED | tojson }}"` attribute
    - Add loading spinner as initial state
    - Conditionally hide section when `AWS_ENABLED` is False
    - Include `<script>` tag for `recommendations.js`
    - _Requirements: 5.1, 5.2, 5.3, 6.2_

- [ ] 8. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The project uses Python (Flask) throughout — all code examples use Python
- Hypothesis is used for property-based testing, compatible with existing pytest setup
- The existing `get_boto_client` pattern (see `comprehend_client.py`) is reused for Bedrock
