# Phase 5 acceptance

- Migration `0016_agent_runs_events` upgrades and downgrades cleanly.
- Duplicate `client_request_id` submissions return the same run.
- A conversation permits only one non-terminal run at a time, enforced by a database uniqueness constraint.
- A reclaimed action-proposal run reuses its existing proposal through `source_agent_run_id`; it cannot create a duplicate proposal.
- Conversations, messages, runs, and events are organization- and owner-scoped.
- The worker reclaims queued and lease-expired runs.
- Safe events are persisted before SSE delivery.
- SSE replays from `Last-Event-ID` or `after_sequence`, sends heartbeat comments, and closes after the terminal event.
- Browser disconnect does not cancel execution.
- Cancellation is idempotent and cooperative.
- Angular uses fetch-based SSE so the sandbox authentication header is preserved.
- Reload reconnects to an active run without resubmitting the message.
- REST fallback remains available.
- No fake progress percentage, timer-generated activity, raw reasoning, tool name, evidence ID, actor ID, or organization ID is displayed.
