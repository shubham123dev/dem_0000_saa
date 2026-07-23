---
kind: business_term
name: Business Glossary
category: business_term
scope:
    - '**'
---

### Nucleus
- Definition：The external organization-management system whose exact table schema (OrganizationAccount, OrganizationPermission, OrganizationCategoryAccess, etc.) is mirrored in this sandbox via an Alembic migration. All read/write access to Nucleus data goes through the framework-neutral `NucleusOrganizationGateway` protocol; the current implementation is a SQLite-backed mock, and a real adapter can be swapped in without changing routes or action handlers.
- Aliases：Nucleus organization schema、Nucleus adapter

### Workplace Agent
- Definition：This project's product name — a governed AI agent that lets users submit natural-language requests which are translated into allowlisted read tools or explicit, approval-gated write actions against the Nucleus organization schema. It enforces per-user/per-organization isolation, immutable audit trails, and separate approval/execution lifecycles.
- Aliases：DBMR Workplace Agent、workplace agent

### Action proposal
- Definition：A dry-run mutation request produced by the agent planner that does not execute until explicitly approved by authorized users. Proposals carry before/after snapshots, risk level, and required approvals; execution is a separate idempotent step that reconciles state and emits durable activity events.
- Aliases：proposal、action_proposal

### Compaction
- Definition：Two-stage context compression for long conversations: macro compaction summarizes older messages non-destructively via overlay records, while micro compaction truncates large tool outputs at read time. Both preserve full fidelity for replay/reconciliation.
- Aliases：macro compaction、micro compaction

### Context memory blocks
- Definition：Per-conversation injectable prompt segments of four types — soul (read-only identity), memory (writable scratchpad with token budgets), searchable knowledge base (FTS5-backed), and loadable skills (large docs loaded on demand). Initialized automatically when a conversation is created.
- Aliases：context blocks、soul block、memory block、knowledge block、skills block

### Test_user1
- Definition：The single production user source for this sandbox. A separate SQL Server connection (not managed by Alembic) provides user directory lookups; writes to this source are disabled by default and gated behind `nucleus_user_writes_enabled`.
- Aliases：test_user1、user directory

### Sandbox
- Definition：Runtime mode (`WORKPLACE_ENVIRONMENT=sandbox`) that enables the raw mock API, disables production database writes, and runs the application with local SQLite. Production mode would require a real Nucleus adapter and different secrets.
- Aliases：sandbox mode
