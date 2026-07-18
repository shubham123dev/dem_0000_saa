# DBMR Workplace Agent — Nucleus Organization Schema Slice

This overlay extends the existing Workplace Agent sandbox at commit
`1aec2a3bb08f79a8a08782596c59533e42916dfa` with a SQLite-backed mock of the
supplied Nucleus organization schema.

## Runtime boundary

```text
Chat or Workplace API
→ authenticated mock user
→ active organization membership
→ backend-owned permission
→ sandbox organization guard
→ exact-schema Nucleus repository
→ SQLite
→ append-only audit
```

Natural-language requests may select allowlisted read tools or create dry-run
action proposals. They cannot approve, execute, choose organization scope, or
supply authorization state.

## Nucleus adapter boundary

Nucleus reads and mutations consume the framework-neutral
`NucleusOrganizationGateway` protocol. The current SQLite repository satisfies
that port structurally. A future real Nucleus adapter can replace the dependency
without changing routes, services, action handlers, approval policy, or model
tool contracts. No production endpoint or credential behavior is invented here.

## Exact SQLite tables

The migration creates these table and column names exactly as supplied:

- `OrganizationAccount`
- `OrganizationCategoryAccess`
- `OrganizationCompanyProfileAccess`
- `OrganizationDrugAccess`
- `OrganizationIndicationAccess`
- `OrganizationMarketAccess`
- `OrganizationPermission`
- `OrganizationReportAccess`

It also creates `nucleus_resource_versions`, an internal Workplace Agent
sidecar used for optimistic concurrency because the supplied tables do not
contain version columns.

The existing lowercase Workplace Agent tables remain unchanged.

## Read tools

Existing tools remain available. Four additional chat tools are registered:

- `get_nucleus_organization_account`
- `get_nucleus_organization_license`
- `get_nucleus_organization_approval_status`
- `get_nucleus_organization_entitlements`

The entitlements result contains rows from all seven supplied access and
permission tables.

## Workplace endpoints

```text
GET /workplace/organizations/{organization_id}/nucleus/account
GET /workplace/organizations/{organization_id}/nucleus/license
GET /workplace/organizations/{organization_id}/nucleus/approval-status
GET /workplace/organizations/{organization_id}/nucleus/entitlements
```

All routes require `X-Mock-User-Id`. Account, licence and approval details are
administrator-only. Entitlement reads are available to active organization
readers and administrators.

## Approval-gated actions

The package keeps all existing actions and adds:

- `update_nucleus_organization_account_field`
- `clear_nucleus_organization_account_field`
- `grant_nucleus_category_access`
- `revoke_nucleus_category_access`
- `grant_nucleus_report_access`
- `revoke_nucleus_report_access`
- `update_nucleus_organization_permissions`

The existing `update_organization_contact_email` action is bridged to the exact
`OrganizationAccount.Email` field and also synchronizes the legacy Overview
profile, so the old chat command and the new exact-schema API cannot drift.

Every write follows:

```text
inspect
→ immutable before/after proposal
→ approval threshold
→ permission, fingerprint and all resource-precondition revalidation
→ optimistic version check
→ idempotent execution
→ exact re-read/reconciliation
→ audit
→ optional separately approved rollback proposal
```

`update_nucleus_organization_permissions` is high risk and requires two
distinct non-requester approvals.

## Safe field policy

Allowlisted `OrganizationAccount` fields:

```text
OrganizationName
OrganizationType
Industry
Website
Email
ContactPersonName
ContactPersonDesignation
ContactPhone
AddressLine1
AddressLine2
City
State
Country
PostalCode
```

Administrative fields are controlled through dedicated actions rather than the generic profile-field action:

```text
UserName                  dedicated identity action, two approvals
MaxUserLimit             dedicated license action, two approvals
LicenseStartDate         dedicated license action, two approvals
LicenseEndDate           dedicated license action, two approvals
Status/IsActive          dedicated lifecycle actions, two approvals
Approval/rejection data  backend-generated actor and UTC time
```

The following remain non-editable identifiers, credentials, and audit-owned fields:

```text
OrganizationAccountId
OrganizationCode
Password
CreatedBy
CreatedDate
UpdatedBy
UpdatedDate
```

`Password` exists only for schema fidelity. It is never included in domain
models, HTTP responses, model evidence, action arguments, or audit details.

## Access mutation boundary

The supplied Category, Report and Permission tables contain `IsActive`, so
those resources support controlled activation/deactivation or exact-row update.

The supplied Company Profile, Drug, Indication and Market tables do not contain
`IsActive`. The workplace layer therefore uses reversible internal tombstones:
the exact source rows remain unchanged, entitlement reads exclude revoked rows,
and approved grant actions can restore them without destructive deletion.

## Administrative-control surface

The sandbox now exposes 30 named write actions. Sensitive username,
licensing, lifecycle and entitlement-revocation operations require two
independent approvals and prohibit requester self-approval. Execution
actor IDs are derived from authenticated backend mappings; the model cannot
provide actor IDs, timestamps, organization scope, permissions, approvals or
idempotency state. This is the same constrained-control pattern used by
mature workplace administration agents; it is not arbitrary SQL access and
it does not advertise production connectivity.
## Governed workplace-resource runtime

The agent can now discover backend-registered internal resources, inspect
their safe field schemas, search within organization scope, and propose
controlled mutations without receiving raw SQL, arbitrary ORM access, table
names, organization scope, actor identity, approval state, or database
credentials. Generic writes are initially enabled for a fully governed
`workplace_setting` resource and safe organization profile fields. Existing
Nucleus, membership, seat, report-access, license and lifecycle operations
continue to use their stronger dedicated handlers. Every generic mutation
persists an immutable snapshot, mutation plan and step receipt; deletion is
soft and tombstoned, and restoration requires a separately approved action.
## Database and seed

Current migration head:

```text
0014_workplace_resources
```

The deterministic idempotent seed adds one synthetic exact-schema account and
representative rows for every supplied access table. No real credentials or
employee data are used.

```powershell
alembic upgrade head
python -m app.db.seed
python -m app.db.seed
```

## Validation

```powershell
python -m compileall -q app tests alembic
alembic current
pytest -q
```

See `APPLY_AND_VALIDATE.md` for the complete Windows PowerShell application,
smoke-test, commit and cleanup sequence.
## Agent-native workplace resources

The chat planner now receives a backend-generated, secret-free resource catalog
and can use five governed resource read tools for discovery, schema inspection,
search, exact lookup and count. Resource routes are canonical: synchronized
organization name and contact-email changes remain on their dedicated Nucleus
handlers, while generic resource writes cannot bypass projection synchronization.
The planner may return `clarification_required` when a business identifier or
other required argument is missing instead of guessing.

Current governed surface:

```text
20 read tools
43 write actions
43 handlers
```


## Final governed workflow milestone

Migration `0015_workplace_workflows` completes the mocked backend workplace-agent
scope with 20 read tools, 43 registered actions/handlers, 42 model-selectable
actions, structured relationship/query intelligence, atomic onboarding and
offboarding, exact Nucleus access packages, query-selected bulk updates,
dynamic risk, durable workflow receipts, reconciliation and separately approved
rollback. The internal exact-snapshot rollback action is never offered to the
model.

See `docs/WORKPLACE_WORKFLOWS.md`.

<!-- ANGULAR_FRONTEND_PHASE_0_CONTRACTS -->
## Angular frontend Phase 0 contracts

The current FastAPI surface is now captured as an executable, commit-pinned
contract inventory for the planned Angular workplace-agent UI. Phase 0 adds no
visual frontend and does not pretend that conversation persistence or streaming
already exists.

See `frontend/README.md` and validate with:

```bash
python scripts/validate_frontend_contracts.py --repo .
pytest -q tests/test_frontend_contracts.py
```
