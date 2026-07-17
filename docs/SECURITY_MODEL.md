# Security Model

## Backend-owned identity and authorization

- Identity comes only from `X-Mock-User-Id` in the sandbox and must resolve to an active user.
- Organization access requires an active membership in the exact requested organization.
- Roles and permissions are loaded from backend tables.
- Authorization never comes from request bodies, query parameters, prompts or model output.
- There is no default administrator.

## Permission families

Read/resource permissions include:

- `organization.profile.read`
- `organization.users.read`
- `organization.seats.read`
- `organization.reports.read`
- `audit.read`

Administrative resource permissions include profile, user, seat and report grant/revoke permissions. Action lifecycle access is separate:

- `agent.actions.read`
- `agent.actions.approve`
- `agent.actions.execute`
- `agent.actions.reconcile`

A lifecycle permission never substitutes for the selected action's resource permission.

## Organization isolation

- Every organization-scoped request checks active membership in that organization.
- Data and audit operations are constrained by `organization_id`.
- Reads do not require a licensed seat.
- Non-sandbox organizations are rejected with `production_access_blocked`.
- Suspended organizations are rejected before business data is returned.

## Fixed tool and action surface

- Seven read tools are allowlisted.
- Nine write action types are allowlisted.
- Model-generated organization IDs, actor IDs, permissions, roles, proposal IDs, approvals, execution commands and idempotency keys are forbidden.
- Natural-language requests can prepare proposals but cannot approve or execute them.
- No arbitrary SQL, unrestricted URL/HTTP execution, shell or browser automation exists.

## Action integrity

- Proposals store normalized arguments, reviewed before/after changes, resource version, approval policy and fingerprint.
- Execution revalidates permissions, fingerprint, approval threshold and resource version.
- Execution is single-use and idempotency-key protected.
- Stale resources are blocked.
- High-risk actions require distinct approvers and disallow requester self-approval.
- Rollback is a new proposal and never runs automatically.

## Audit and uncertain outcomes

- Successful business reads append organization-scoped audit events.
- Action proposal, approval/rejection, execution and reconciliation transitions are audited.
- Audit-log reads are not audited to avoid recursive growth.
- A successful mutation is not reversed solely because audit persistence failed.
- Audit replay persists the missing audit record without repeating the mutation.
- Uncertain provider outcomes require bounded reconciliation by inspection.

## Secret and error policy

- Responses use a consistent error contract with a request ID.
- Stack traces, database paths, SQL and secrets are not returned.
- `.env` is ignored; `.env.example` contains only local defaults.
- Seed identities are synthetic.
