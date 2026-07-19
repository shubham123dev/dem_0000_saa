# Phase 6 acceptance

- Capability catalogue is derived from the backend registry, handlers, permissions, and organization state.
- Approval Center uses real proposals and safe projections.
- Backend controls every allowed operation.
- Approval never executes automatically.
- Explicit execution is idempotent.
- Execution events are durable, ordered, replayable, and streamed with SSE.
- Stale actions cannot execute and uncertain outcomes require reconciliation.
- Receipts and governed rollback proposals are available.
- Ask AI opens the exact proposal when a proposal reference is available.
- No fake progress, raw arguments, fingerprints, actor IDs, or hidden reasoning is shown.
