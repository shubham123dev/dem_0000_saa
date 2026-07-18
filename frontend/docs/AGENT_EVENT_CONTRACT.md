# Angular normalized UI event contract

## Status

This is the planned frontend-facing envelope for the Angular application. It does **not** claim that an SSE or WebSocket endpoint exists today. The current agent query endpoint returns a final `AgentQueryResponse`.

The schema is `frontend/contracts/ui-event.schema.json`.

## Purpose

The UI needs one stable stream vocabulary even though the backend currently exposes several REST response types. The future transport layer will normalize backend state into these events:

- `assistant_message`
- `clarification`
- `activity_update`
- `proposal`
- `approval_update`
- `execution_update`
- `receipt`
- `reconciliation`
- `error`

## Safe activity visibility

`activity_update` contains a concise operational summary such as:

- Understanding request
- Resolving resources
- Checking permissions
- Evaluating risk
- Preparing proposal
- Executing a durable workflow step
- Verifying outcome

It must never carry hidden prompts, private model chain-of-thought, credentials, raw SQL, unrestricted database fields, or internal exception traces.

## Ordering and replay

Every future streamed event must contain:

- `event_id`: stable deduplication identifier.
- `conversation_id`: UI conversation scope.
- `occurred_at`: server timestamp.
- `request_id`: correlation identifier when available.
- `type` and typed `payload`.

The future client must deduplicate by `event_id` and restore durable proposal/execution state through existing GET endpoints after reconnect. Mutations must never be automatically retried.

## Current fallback

Until streaming is implemented, Angular will:

1. submit the query through the current REST endpoint;
2. render its final mode;
3. poll/get proposal state only when necessary;
4. execute explicit approve/reject/execute commands;
5. avoid fake timer-based planning stages.
