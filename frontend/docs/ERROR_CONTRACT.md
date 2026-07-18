# Frontend error contract

## Wire envelope

```json
{
  "error": {
    "code": "agent_action_stale",
    "message": "The reviewed resource state changed before execution.",
    "request_id": "req_phase0_001"
  }
}
```

The same request ID is returned in `X-Request-Id`.

## Current backend codes

`unauthenticated`, `user_disabled`, `organization_not_found`, `organization_suspended`, `report_not_found`, `organization_access_denied`, `permission_denied`, `production_access_blocked`, `agent_model_unavailable`, `agent_model_request_failed`, `agent_model_response_invalid`, `agent_tool_call_invalid`, `agent_action_invalid`, `agent_action_proposal_not_found`, `agent_action_state_conflict`, `agent_action_limit_exceeded`, `agent_action_expired`, `agent_action_stale`, `agent_action_cancelled`, `agent_action_already_decided`, `agent_action_execution_in_progress`, `agent_action_reconciliation_required`, `agent_action_idempotency_conflict`, `agent_action_rollback_unavailable`, `workplace_resource_invalid`, `workplace_resource_not_found`, `internal_error`.

## Angular normalization policy

The future Angular error mapper will produce:

```ts
interface WorkplaceError {
  code: string;
  title: string;
  message: string;
  requestId?: string;
  retryable: boolean;
  suggestedAction: 'retry' | 'refresh' | 'request_new_proposal' | 'contact_admin' | 'none';
}
```

The UI must never display Python exception names, stack traces, SQL text, or arbitrary backend payloads.

## Important current behavior

FastAPI request-validation failures return HTTP 422 with code `internal_error` and message `Request validation failed.` The Angular mapper must treat that combination as a non-retryable invalid request until a dedicated validation code is introduced.
