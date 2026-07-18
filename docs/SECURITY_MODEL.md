# Security model

## Backend-owned authorization

- Identity comes from `X-Mock-User-Id` only in the sandbox.
- Roles and permissions come from database rows, never prompts or request text.
- Organization scope comes from the route and membership check, not model output.
- Production organizations remain blocked.

## New permissions

- `organization.account.read`: administrator-only account/licence/approval read.
- `organization.account.update`: allowlisted account profile/contact proposals.
- `organization.entitlements.read`: active reader/admin entitlement read.
- `organization.entitlements.update`: administrator-only entitlement proposals.

Lifecycle permissions remain separate from resource permissions. An approver or
executor needs both the action-management permission and the selected action's
resource permission.

## Secret boundary

`OrganizationAccount.Password` is mapped only to preserve schema fidelity.
There is no password domain field, API field, chat tool argument, action,
evidence item or audit detail.

`UserName`, account code, licence fields, approval fields, status and active
state are also protected from general account-field actions.

## High-risk permission changes

`update_nucleus_organization_permissions` requires two distinct approvers and
disallows requester self-approval. It targets one exact
`OrganizationPermissionId`; it never silently edits an arbitrary first row.

## Non-destructive access handling

Category and Report revocation set `IsActive = false`. Permission rollback of a
newly created row deactivates it because no physical-delete contract was
provided. Company, Drug, Indication and Market access remain read-only until a
safe lifecycle contract is supplied.
## Multi-resource review binding

New action proposals persist a canonical list of every reviewed resource and
observed version. Fingerprint version 3 covers that complete list, while
migrated version-2 proposals retain their original verification semantics.
Execution re-prepares and compares all preconditions before consuming the
approval. Cross-store reconciliation repairs only an unchanged reviewed
projection and never overwrites a conflicting newer value.
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
