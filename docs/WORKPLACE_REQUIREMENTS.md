# Workplace Agent — Requirements (Step 0)

## Product boundary

- The existing SARA/chatbot remains in its own repository and is not integrated here.
- This repository must not contain SARA adapters, SARA API clients, SARA credentials, chatbot gateways or chatbot-specific permissions.
- Workplace Agent is a separate backend/product area.
- Initial users are internal company users represented by synthetic sandbox identities.
- Initial environment is sandbox only; production access is blocked.
- Current Nucleus administration pages are a frontend/sessionStorage prototype.
- Real Nucleus APIs and the live organization database are not available yet.
- Automated test doubles, fixtures and test-only helpers belong under `tests/`, not under `app/`.

## Step 0 scope

Step 0 provides a production-structured mock foundation for:

```text
X-Mock-User-Id
→ active user
→ active organization membership
→ backend-owned role/permission check
→ sandbox organization guard
→ mock organization adapter/API
→ SQLite sandbox database
→ append-only audit event
```

Read capabilities:

- organization profile
- organization users/memberships
- seat entitlement and calculated usage
- report catalog with organization access
- exact organization/report access check

## Business rules

- Users and seats are different entities.
- An organization may contain any number of users.
- Seat usage is calculated from active seat assignments; it is never stored as a counter.
- Report access belongs to the organization.
- Administrative reads require active user + active membership + permission, but not an active seat.
- Any future agent/model integration must use a provider-neutral contract owned by this repository; tests must use test doubles under `tests/`.

## Explicit non-goals

No SARA integration, LLM planner, write execution, approval flow, arbitrary SQL, arbitrary HTTP, shell access, browser automation, production integration, real employee data, billing mutation, API-key creation, security-policy mutation or frontend code.

## Guardrails

- Permissions are resolved only from backend data.
- Prompt text cannot grant authorization.
- Service/API layers depend on adapter contracts, not ORM objects.
- Audit events are append-only.
- Raw mock API is disabled by default and may be enabled only in sandbox.
- API errors do not leak SQL, paths, stack traces or secrets.
