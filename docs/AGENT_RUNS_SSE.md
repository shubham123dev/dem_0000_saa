# Durable agent runs and resumable SSE

Phase 5 introduces an organization- and owner-scoped command protocol around the existing governed agent pipeline.

## Command and event flow

1. `POST /workplace/organizations/{organization_id}/agent/runs` authorizes the user, creates or resumes a conversation, persists a user message, and creates an idempotent queued run.
2. A database-leased worker claims the run and executes the existing authorization, planning, read-tool, proposal, and synthesis services.
3. Safe operational events are committed to `agent_run_events` before delivery.
4. `GET .../events` replays events after `Last-Event-ID` or `after_sequence` and follows the run until a terminal event.
5. Browser disconnect never cancels a run. Cancellation is an explicit idempotent command and is observed cooperatively at backend checkpoints.

## Durability

The database is the authority for conversations, normalized messages, runs, leases, and events. `client_request_id` prevents duplicate run creation. A database active-slot constraint prevents overlapping runs inside one conversation. `source_agent_run_id` prevents a reclaimed action-proposal run from creating a second proposal.

The web process can host the sandbox coordinator through FastAPI lifespan. The same coordinator is executable independently with `python -m app.agent_run_worker` for deployment separation.

## Safety

Events contain fixed operational stages and backend-owned safe messages. They do not contain model chain-of-thought, hidden prompts, raw tool arguments, SQL, credentials, raw evidence, or unfiltered provider responses.

## Deliberate transport choices

- REST: submit, inspect, and cancel commands.
- SSE: server-to-browser progress and terminal results.
- Webhooks: deferred to the provider-integration phase, after durable run correlation exists.
- WebSockets: deferred until a real bidirectional realtime use case exists.
