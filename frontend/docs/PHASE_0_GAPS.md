# Phase 0 gap register

Phase 0 recorded missing interfaces instead of inventing them. This register now tracks which contracts have been implemented.

| Gap | Current state | Required owner/phase |
|---|---|---|
| Conversation persistence API | Resolved in Phase 5: organization-scoped durable conversations and normalized messages are authoritative on the backend. | Complete. |
| Streaming transport | Resolved in Phase 5: fetch-based, authenticated, resumable SSE with persisted replay and heartbeat comments. | Complete. |
| Live activity trace | Resolved in Phase 5: safe operational events are emitted at real backend boundaries; private reasoning remains forbidden. | Complete. |
| Stable execution-step endpoint | Execution response remains generic `result: object`; no dedicated public step schema exists. | Backend workflow-read projection phase. |
| Current-user endpoint | Sandbox identity is supplied through `X-Mock-User-Id`. | Authentication integration phase. |
| Request-changes decision | Current decisions are approve, reject, cancel. | Product decision before adding a new backend action. |
| Proposal-specific audit detail | Organization audit log and audit replay exist; no dedicated proposal audit-detail route. | Audit UI/backend projection phase. |
| Direct related-resource HTTP route | Relationship intelligence is available through agent tools, not a dedicated REST route. | Resource context phase if direct navigation needs it. |
| File upload | No agent attachment/upload contract exists. | Attachment phase. |
| Cross-origin browser policy | The Angular application uses a same-origin `/api` proxy; no separate cross-origin deployment contract is defined. | Deployment hardening phase if origins split. |
| Production authentication | Out of the mocked backend scope. | Real integration phase. |
| External provider webhooks | No provider-specific signed webhook receiver exists. | Phase 6 after durable run correlation. |
| Bidirectional realtime transport | No WebSocket contract exists because Phase 5 requires only server-to-browser progress. | Add only for a genuine bidirectional use case. |

## Phase 5 boundary

The browser submits commands over REST and receives progress/results through SSE. The event journal stores safe operational status only. It never stores model chain-of-thought, hidden prompts, raw tool arguments, SQL, credentials, or unfiltered provider responses.

The original `/agent/query` endpoint remains available as an explicit REST compatibility path.
