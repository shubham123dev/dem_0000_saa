# Phase 5 durable conversations and resumable SSE

Phase 5 replaces browser-owned context assembly with durable backend conversations and agent runs.

- REST submits commands and cancellation requests.
- A database-leased worker executes queued runs through the existing governed agent pipeline.
- Every safe activity event is committed before delivery.
- Fetch-based SSE replays events using `Last-Event-ID` and `after_sequence`.
- Browser disconnects stop watching only; they do not cancel the run.
- Cancellation is cooperative and becomes final only when the worker reaches a checkpoint.
- The existing `/agent/query` endpoint remains a compatibility fallback.

Activity describes operational stages such as access checking, planning, resource reading, proposal preparation, and answer preparation. It never exposes model chain-of-thought, prompts, raw tool arguments, SQL, credentials, or unfiltered provider output.

## Transport boundary

REST creates and controls runs. Authenticated fetch-based SSE replays and follows persisted events. Webhooks are intentionally deferred until a provider-specific external operation can be correlated to a durable run; WebSockets are intentionally absent because this phase has no bidirectional realtime requirement.
