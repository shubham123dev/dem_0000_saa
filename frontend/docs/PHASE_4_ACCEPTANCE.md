# Phase 4 acceptance

Phase 4's reusable conversation UI remains accepted when:

- read, clarification, and action-proposal modes render correctly;
- no raw evidence ID, tool name, proposal ID, organization ID, or actor ID is displayed;
- Enter sends and Shift+Enter inserts a line;
- proposal cards navigate to Pending approvals and do not approve or execute;
- safe errors never expose stack traces or raw provider payloads.

## Superseded by Phase 5

The original one-shot REST transport, browser-built clarification context, and full current-tab message snapshot were transitional boundaries. Phase 5 replaces them with durable backend conversations, idempotent runs, persisted safe events, resumable fetch-based SSE, and lightweight recovery identifiers. The REST path remains tested as a compatibility fallback.
