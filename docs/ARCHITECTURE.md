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
→ proposal fingerprint recheck
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

The existing `update_organization_contact_email` action now uses the exact
Nucleus account as canonical storage and keeps the legacy Overview profile in
sync.

## Future replacement

```text
Current: NucleusOrganizationGateway → NucleusOrganizationRepository → SQLite exact-schema mock
Future:  NucleusOrganizationGateway → NucleusOrganizationApiAdapter → real Nucleus API/database mapping
```

Routes and chat tools consume stable domain contracts, so the future adapter can
replace persistence without exposing raw production schemas to the frontend or
model.
