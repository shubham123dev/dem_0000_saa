# Security Model (Step 0)

## Backend-owned authorization

- Identity comes only from `X-Mock-User-Id` and must resolve to an active user.
- Organization access requires an active row in `organization_memberships`.
- Roles and permissions are stored in `organization_memberships` and `role_permissions` and are enforced by the backend permission service.
- Authorization is never derived from request bodies, query parameters, prompts or user-provided text.
- There is no default administrator.

## Current roles

Both roles receive the implemented read permissions. `sandbox_admin` also receives reserved organization-management write permissions for later controlled phases, but Step 0 exposes no write routes.

Current read permissions are:

- `organization.profile.read`
- `organization.users.read`
- `organization.seats.read`
- `organization.reports.read`
- `audit.read`

## Organization isolation

- Every organization-scoped request verifies active membership in that exact organization.
- Data and audit queries are constrained by `organization_id`.
- Administrative reads do not require a seat; membership and permission are the authorization boundary.

## Sandbox-only enforcement

- Only organizations with `environment = sandbox` are accessible.
- Non-sandbox access is rejected with `production_access_blocked`.
- Production credentials and integrations are out of scope.

## Fixed tool surface

- Five read-only workplace tools are implemented.
- No arbitrary SQL, URL/HTTP execution, shell access, browser automation or LLM planner exists.
- No workplace `POST`, `PUT`, `PATCH` or `DELETE` route exists.

## Repository separation

- SARA/chatbot runtime code, clients, credentials, gateways and permissions are not part of this repository.
- Any future model/provider integration must use a provider-neutral Workplace Agent contract.
- Fake providers, fixtures and deterministic responses belong under `tests/` only.

## Audit requirements

- Every successful business read appends an immutable audit event.
- Audit rows are not updated or deleted by application behavior.
- Audit events record actor, organization, event type, operation, outcome, resource and structured details.
- Reading the audit log is not itself audited to avoid recursive growth.

## Secret and error policy

- Error responses use a consistent contract with a generated `request_id`.
- Responses do not expose stack traces, database paths, SQL or secrets.
- `.env` is ignored; `.env.example` contains only non-secret local defaults.
- Seed identities and email addresses are synthetic.
