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
→ permission and fingerprint revalidation
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

Protected fields are not chat-editable in this slice:

```text
OrganizationAccountId
OrganizationCode
UserName
Password
MaxUserLimit
LicenseStartDate
LicenseEndDate
Status
ApprovedBy
ApprovedDate
RejectedBy
RejectedDate
RejectionReason
IsActive
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
`IsActive`, timestamps, or a stated delete contract. They are intentionally
read-only in this package rather than inventing destructive behavior.

## Database and seed

Current migration head:

```text
0011_nucleus_organization_schema
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
