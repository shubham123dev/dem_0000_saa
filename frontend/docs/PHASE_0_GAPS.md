# Phase 0 gap register

Phase 0 records missing interfaces instead of inventing them.

| Gap | Current state | Required owner/phase |
|---|---|---|
| Conversation persistence API | No conversation/session endpoints are registered. | Backend contract extension before persistent history UI. |
| Streaming transport | No SSE or WebSocket agent-event endpoint exists. | Backend streaming phase. |
| Live activity trace | Agent query returns only a final response. | Backend safe activity events; UI must not fake them. |
| Stable execution-step endpoint | Execution response is generic `result: object`; no dedicated public step schema exists. | Backend workflow-read projection. |
| Current-user endpoint | Sandbox identity is supplied through `X-Mock-User-Id`. | Authentication integration phase. |
| Request-changes decision | Current decisions are approve, reject, cancel. | Product decision before adding a new backend action. |
| Proposal-specific audit detail | Organization audit log and audit replay exist; no dedicated proposal audit-detail route. | Audit UI/backend projection phase. |
| Direct related-resource HTTP route | Relationship intelligence is available through agent tools, not a dedicated REST route. | Resource context phase if direct navigation needs it. |
| File upload | No agent attachment/upload contract exists. | Attachment phase. |
| Cross-origin browser policy | No dedicated Angular-origin CORS contract is documented here. | Angular integration phase. |
| Production authentication | Out of the mocked backend scope. | Real integration phase. |

## Non-blocking for Phase 0

These gaps do not invalidate the existing governed backend. They prevent the frontend from pretending features exist before their contracts are added.

<!-- ANGULAR_FRONTEND_PHASE_1_STATUS -->
## Status after Phase 1

Phase 1 closes the missing Angular runtime, runtime configuration, typed API
facade, request correlation, sandbox-auth interceptor, runtime response
validation, unit-test foundation and Playwright foundation.

Conversation persistence, SSE/WebSocket streaming, backend activity events,
execution-step projections, file upload and request-changes behavior remain
unimplemented. The Angular application explicitly uses `streamTransport: rest`
and does not simulate any of those capabilities.
