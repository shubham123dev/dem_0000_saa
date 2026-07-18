# Phase 4 Ask AI conversation

Phase 4 connects the existing Angular shell to the current REST agent endpoint.

## Current transport truth

The backend accepts one `query` and returns one final response. It does not expose a conversation ID, persisted history, SSE, WebSocket, token stream, or live planning trace. The UI therefore shows a clear pending state and then renders the final response; it never fabricates intermediate reasoning.

## Supported response modes

- `read`: assistant answer plus a safe count of verified backend sources.
- `clarification_required`: assistant question and human-readable missing fields. The next reply is transparently combined with the original request because the backend endpoint is stateless.
- `action_proposal`: safe proposal summary with risk, status, expiration, and bounded change summaries. Review opens Pending approvals; Phase 4 does not approve or execute from chat.

## Persistence boundary

Normalized messages are stored in `sessionStorage` for the current browser tab only. Raw evidence IDs, tool names, organization IDs, proposal IDs, API result payloads, and actor IDs are not persisted or displayed. Closing the tab clears browser history; no server-side conversation history is claimed.

## Request safety

Requests are never automatically retried. Stopping a request only stops the browser from waiting and explicitly warns that the backend may have completed the read or proposal. Manual retries warn users to check Pending approvals first.
