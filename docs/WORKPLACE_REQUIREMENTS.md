# Workplace Agent — Sandbox Requirements

## Product boundary

- The existing SARA/chatbot remains in its own repository.
- Workplace Agent owns a separate backend and stable API contracts.
- Initial identities and organization records are synthetic sandbox data.
- Production organization access is blocked.
- Current Nucleus pages may remain static until real APIs and schema are available.
- Frontend code must consume stable Workplace contracts, not raw SQLite or future Nucleus fields.
- Test doubles, fixtures and deterministic model responses belong under `tests/`.

## Current sandbox scope

```text
X-Mock-User-Id
→ active user
→ active organization membership
→ backend-owned resource permission
→ backend-owned action-management permission
→ sandbox organization guard
→ allowlisted read or immutable action proposal
→ approval policy
→ version-checked execution
→ verification, audit, reconciliation and rollback proposal
```

## Read capabilities

- organization overview;
- organization profile;
- users and memberships;
- seat entitlement and calculated usage;
- report catalogue with organization access;
- exact report-access decision;
- organization audit log.

The overview is a stable page-level contract for the Nucleus dashboard. It includes renewal, workspace health, licensed modules, available areas and organization login count.

## Controlled action capabilities

- update organization contact email;
- invite and activate a user;
- update membership role;
- remove a user;
- assign and revoke seats;
- grant and revoke report access.

Every action requires an immutable dry run, explicit approval, execution-time permission/version validation, idempotency and audit. High-risk actions use two distinct approvers.

## Business rules

- Users and seats are different entities.
- Seat usage is calculated from active assignments.
- Report access belongs to the organization.
- Administrative reads require active user, active membership and permission, but not a seat.
- The last active administrator cannot be demoted or removed.
- A seated member must be unseated before removal.
- The model cannot choose organization scope, identity, permissions, approval state or execution identifiers.
- The real Nucleus adapter must preserve the stable gateway and API contracts.

## Current non-goals

- production credentials or production organization mutations;
- arbitrary SQL, unrestricted HTTP, shell or browser execution;
- real billing payments;
- unrestricted API-key creation;
- replacing the existing SARA runtime;
- final real Nucleus field mappings before the provider API/schema is available.

## Guardrails

- Raw mock API is disabled by default.
- API errors do not leak SQL, paths, stack traces or secrets.
- Audit events are append-only; failed audit persistence is replayed without repeating the business mutation.
- Reconciliation inspects uncertain outcomes without automatically repeating an unapproved mutation.
