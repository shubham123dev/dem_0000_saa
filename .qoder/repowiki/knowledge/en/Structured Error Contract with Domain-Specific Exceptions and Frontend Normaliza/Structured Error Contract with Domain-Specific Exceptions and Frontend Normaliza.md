---
kind: error_handling
name: Structured Error Contract with Domain-Specific Exceptions and Frontend Normalization
category: error_handling
scope:
    - '**'
source_files:
    - app/core/errors.py
    - app/agent/action_errors.py
    - app/workplace_resources/errors.py
    - app/main.py
    - frontend/src/app/core/errors/workplace-api.error.ts
    - frontend/src/app/core/api/api-error.interceptor.ts
    - frontend/src/app/core/errors/error-normalizer.ts
    - app/repositories/agent_action_repository.py
---

The codebase implements a layered, contract-driven error handling strategy across the FastAPI backend and Angular frontend, centered on a single AppError base class and a stable set of string error codes.

Backend exception hierarchy — All domain errors subclass app.core.errors.AppError, which carries three fields: code (a stable string from the ERROR_CODES frozenset), status_code (HTTP status), and message. Concrete subclasses live in app/core/errors.py (authentication/authorization, organization, agent run/conversation) and are extended per domain in app/agent/action_errors.py (action lifecycle states like stale, expired, already decided, idempotency conflict) and app/workplace_resources/errors.py (resource-level not found / invalid). A separate AgentActionTransitionConflictError(RuntimeError) is raised deep in repositories (app/repositories/agent_action_repository.py) and re-raised as an AppError by the service layer so it still maps to a documented code.

Global exception handlers — register_exception_handlers() (called once in app/main.py) registers four Starlette/FastAPI handlers that convert every exception into a uniform JSON envelope {error: {code, message, request_id}} and echo back the X-Request-Id header. Handlers cover: AppError subclasses, StarletteHTTPException (mapped to unauthenticated/permission_denied/organization_not_found/internal_error), RequestValidationError (422 -> internal_error), and a catch-all Exception that logs via logger.exception and returns 500.

Request-id propagation — An HTTP middleware in create_app() injects request.state.request_id (from the incoming X-Request-Id header or a generated UUID) and mirrors it on the response; all error bodies include this id for tracing.

Frontend error model — The Angular app defines WorkplaceApiError (frontend/src/app/core/errors/workplace-api.error.ts) carrying status, code, message, and optional requestId. The api-error.interceptor.ts parses the server's error envelope using the shared errorEnvelopeSchema, normalizes network failures and unexpected payloads into WorkplaceApiError, and forwards them up the RxJS chain.

Client-side normalization — normalizeWorkplaceError() (frontend/src/app/core/errors/error-normalizer.ts) maps backend codes to user-facing WorkplaceErrorView objects with a retryable flag and a suggestedAction ('retry' | 'refresh' | 'request_new_proposal' | 'contact_admin' | 'none'). It treats agent_action_expired|stale|cancelled as non-retryable proposals requiring a refresh, groups agent_model_request_failed|agent_model_unavailable|internal_error plus any 5xx/network failure as retryable, and special-cases permission-denied flows.

Conventions developers should follow:
- Never raise bare Exception or ValueError from API paths; wrap business violations in the appropriate AppError subclass so the global handler can emit a stable code.
- Add new error codes only by defining a subclass of AppError and registering the code in ERROR_CODES; never invent ad-hoc strings.
- Let repository-layer state-machine transitions raise AgentActionTransitionConflictError; let the service layer translate it to a documented action error.
- Do not swallow exceptions in route handlers — propagate them so the global handlers attach request_id and return the canonical envelope.
- On the frontend, always construct WorkplaceApiError through the interceptor or schema validation; use normalizeWorkplaceError to derive UI actions rather than hard-casing on codes.