# Security Model (Step 0)

## Backend-owned permissions

- Roles and permissions live in the database (`employee_organization_roles`,
  `role_permissions`) and are enforced by the backend permission service.
- Authorization is **never** derived from the request body, query parameters,
  headers (beyond employee identity), or any user-provided text.
- There is **no default admin**. When the `X-Mock-Employee-Id` header is absent,
  the request is `unauthenticated`.

### Roles and permissions

| Role | Permissions |
| ---- | ----------- |
| `sandbox_admin` | `organization.profile.read`, `organization.profile.update`* |
| `sandbox_reader` | `organization.profile.read` |

\* `organization.profile.update` exists in the model for future steps. Step 0
exposes and executes **no** update endpoint or write tool.

## Organization isolation

- Every organization-scoped request verifies the employee has a role in that
  specific organization before any data is returned.
- Audit events are queried strictly by `organization_id`, so one organization's
  audit log never includes another's events.

## Sandbox-only enforcement

- Only organizations with `environment = sandbox` are accessible.
- Any non-sandbox organization access is rejected with
  `production_access_blocked`.
- Production access, production credentials, and production integrations are
  entirely out of scope.

## No prompt-provided authorization

- The system does not accept roles, permissions, or authorization claims from
  prompts or user text. Identity comes only from the mock auth header and is
  resolved against the database.

## No arbitrary tools

- No arbitrary SQL execution, no arbitrary URL/HTTP execution, no shell tools,
  no browser automation, and no LLM planner exist in Step 0.
- The only tool is the read-only `get_organization_profile`.

## Audit requirements

- Every successful profile read appends an **append-only** audit event.
- Audit rows are never updated or deleted by application behavior.
- Audit events capture actor, organization, event type, operation, outcome,
  resource, and structured details.

## Secret-redaction policy

- API error responses use a single consistent contract with a generated
  `request_id` and never leak stack traces, database paths, SQL, or secrets.
- Full exception detail is logged server-side only.
- No secrets or personal information are committed; `.env` is git-ignored and
  only `.env.example` (with placeholder values) is tracked.
- Employee emails are synthetic test values (`*@example.test`).

## Production access blocked

- Production is explicitly blocked at the service layer via sandbox-only
  enforcement and advertised as `production_access: false` on
  `GET /workplace/capabilities`.
