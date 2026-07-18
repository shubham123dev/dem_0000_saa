# Governed Workplace Workflows

The mocked backend workplace agent completes its scoped workflow layer in
`0015_workplace_workflows`.

## Final governed surface

- 20 read tools
- 43 registered actions
- 43 handlers
- 42 model-selectable actions
- 1 internal-only rollback action

The internal action `restore_workplace_resource_snapshots` is never included in
the model catalog. It can be created only by the backend rollback service after
a successful reversible action.

## Structured query language

Advanced reads and query-selected bulk mutations accept a JSON object with
`all` and `any` arrays. Each condition contains `field`, `operator`, and, where
required, `value`.

Supported operators:

- `equals`
- `not_equals`
- `contains`
- `starts_with`
- `in`
- `greater_than`
- `less_than`
- `between`
- `is_null`
- `is_not_null`

Only registry fields marked searchable are accepted. The model never supplies
SQL, ORM names, database columns, organization scope, actor identity, approval
state, or execution identifiers.

## Relationships

The relationship registry exposes backend-owned links among organizations,
memberships, users, seat pools, assignments, report access, reports, settings,
the Nucleus account, and Nucleus entitlement rows. Relationship traversal is
organization-scoped and limited to registered paths.

## Composite workflows

### Onboard organization user

The workflow creates or reactivates the user and membership and optionally
assigns a standard seat. All changes execute in one database transaction.
Administrator onboarding is dynamically high risk; normal reader onboarding is
medium risk.

### Offboard organization user

The workflow revokes active seat assignments and removes the membership in one
transaction. It blocks self-offboarding and removal of the last active
administrator. Report access is not modified because the current schema models
it at organization scope rather than user scope.

### Apply organization access package

A single reviewed package can grant or revoke category, company-profile, drug,
indication, market, and report access in the exact Nucleus schema. The workflow
uses `IsActive` where the source table has it and tombstones where it does not.
The authenticated Nucleus actor mapping is mandatory.

### Query-selected bulk update

The backend resolves the structured query, freezes the exact target IDs and
versions, hashes the target set, and places the complete before/after preview in
the proposal. Any target-set or version drift marks execution stale.

## Dynamic risk

Risk is calculated during preparation and frozen in fingerprint version 4.
High risk requires two independent approvals and forbids self-approval.
Destructive changes, administrator changes, more than five affected resources,
or more than three access changes are high risk.

Existing fingerprint versions 2 and 3 remain valid for already-persisted
proposals.

## Atomicity, receipts, reconciliation, and rollback

Composite workflows write one mutation plan and ordered step receipts. Same-
database workflow changes commit atomically. Reconciliation re-reads the exact
intended final state. Rollback is always a separate proposal and uses either a
backend-defined inverse workflow or the internal exact-snapshot restore action.
