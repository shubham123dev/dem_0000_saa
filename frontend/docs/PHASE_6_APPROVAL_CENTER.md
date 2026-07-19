# Phase 6 Approval Center

The Approval Center is the user-facing governed action control plane.

- Backend-derived allowed operations decide which controls appear.
- Medium/high risk is prominent; high-risk approval and execution require typed confirmation.
- Approval and execution are separate operations.
- Execution activity comes from persisted backend events, not timers.
- Reload and reconnect reuse the same execution idempotency key.
- Stale proposals cannot execute.
- Reconciliation is required for uncertain outcomes.
- Rollback creates a new reviewable proposal rather than reversing immediately.
