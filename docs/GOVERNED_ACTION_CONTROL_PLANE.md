# Governed action control plane

Phase 6 makes the existing workplace action lifecycle fully usable from the Angular application.

A model may inspect workspace state and prepare a dry-run proposal. It cannot approve, reject, cancel, execute, reconcile, or roll back its own proposal. Those operations require explicit authenticated API calls and backend permission checks.

The lifecycle is:

`inspect → propose → approve or reject → explicit execute → verify → receipt → reconcile or rollback proposal`

Approval never automatically executes. Execution uses a stable browser-generated idempotency key. Real backend boundaries append safe durable events which are replayed over authenticated SSE. A network disconnect never repeats the administrative mutation.

Receipts expose safe before/after projections, the human executor label, timestamps, and outcome. They never expose fingerprints, raw arguments, database versions, actor IDs, provider payloads, or hidden reasoning.
