# Phase 4 Ask AI conversation

Phase 4 established the Angular conversation presentation: composer behavior, normalized read answers, clarification rendering, reviewable proposal cards, bounded errors, and an explicit REST compatibility path.

## Status after Phase 5

The presentation components remain in use, but Phase 5 supersedes the Phase 4 transport and persistence boundary:

- durable conversations and normalized messages are authoritative on the backend;
- commands create idempotent agent runs;
- safe operational activity and terminal results arrive through resumable SSE;
- the browser stores only recovery identifiers and the last delivered sequence;
- clarification context is assembled by the backend conversation service;
- `/agent/query` remains available only as the explicit REST fallback.

Phase 4's security rule remains unchanged: raw evidence IDs, tool arguments, actor IDs, organization IDs, hidden prompts, and private reasoning are not rendered in conversation UI.
