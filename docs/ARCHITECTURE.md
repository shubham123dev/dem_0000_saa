# Architecture

## Repository boundary

This repository contains the standalone Workplace Agent backend and an isolated
Angular demonstration workspace. The current package changes backend code only.
The existing SARA/chatbot repository remains separate.

## Exact-schema read flow

```text
Workplace route or chat tool
→ X-Mock-User-Id
→ active user
→ active organization membership
→ backend-owned permission
→ sandbox/active organization guard
→ NucleusOrganizationGateway port
→ NucleusOrganizationRepository SQLite adapter
→ exact PascalCase SQLite tables
→ stable domain/HTTP contract
→ append-only audit
```

`OrganizationCode` joins the existing stable string organization scope to the
integer `OrganizationAccountId` schema.

## Write flow

```text
allowlisted action request
→ normalize exact arguments
→ inspect exact row
→ immutable before/after proposal
→ approval policy
→ final authorization recheck
→ proposal fingerprint and all resource-precondition recheck
→ sidecar version compare-and-advance
→ exact row mutation
→ deterministic result
→ audit/reconciliation
```

The supplied Nucleus tables have no version columns. The internal
`nucleus_resource_versions` sidecar provides optimistic concurrency while
leaving the supplied tables unchanged.

## Compatibility bridge

The existing Overview/profile tables remain the trusted authorization and
frontend compatibility surface. Updates to `OrganizationAccount.OrganizationName`,
`Email` and `OrganizationType` synchronize their overlapping legacy values in
the same SQLite transaction.

The existing `update_organization_contact_email` action uses the exact Nucleus
account as canonical storage and coordinates the legacy Overview projection at
the action layer. OrganizationName, Email and OrganizationType proposals bind
approval to both reviewed resource versions. A partial cross-store outcome is
reconciled without silently overwriting an unexpected concurrent value.

## Future replacement

```text
Current: NucleusOrganizationGateway → NucleusOrganizationRepository → SQLite exact-schema mock
Future:  NucleusOrganizationGateway → NucleusOrganizationApiAdapter → real Nucleus API/database mapping
```

Routes and chat tools consume stable domain contracts, so the future adapter can
replace persistence without exposing raw production schemas to the frontend or
model.
## Nucleus full administrative control

Nucleus administrative writes are exposed only as named backend-owned
actions. Profile fields remain low risk; username, license and lifecycle
transitions require two independent approvals. Authenticated Workplace user
IDs resolve to integer Nucleus actors through an internal mapping and the
execution record preserves the original executor for deterministic
reconciliation. Company-profile, drug, indication and market revocations use
reversible tombstones because those supplied tables do not contain
`IsActive`; exact source rows are never physically deleted by this package.
Password is outside every action, model, response and audit contract.
## Governed workplace-resource runtime

Internal resource discovery and mutation are driven by a backend registry
that maps public business fields to exact ORM attributes, nullability,
visibility, searchability and mutation policy. The model never supplies a
physical table name, ORM attribute, organization scope, actor identity,
permission, approval or SQL expression. Generic execution is limited to
registered operations, freezes exact resource versions in the approved
proposal, records immutable snapshots and per-step receipts, and uses
reversible soft deletion with tombstones. Sensitive or cross-resource
domains such as Nucleus identity, licensing, lifecycle, seats and access
continue through dedicated handlers with stronger invariants.
