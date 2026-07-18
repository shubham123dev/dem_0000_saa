# Source-state audit

## Repository baseline

- Repository: `shubham123dev/dem_0000_saa`
- Branch: `main`
- Base commit: `1aec2a3bb08f79a8a08782596c59533e42916dfa`
- Base feature: completed Organization Overview vertical slice
- Base migration: `0010_add_organization_overview`

## Existing behavior preserved

- Overview/profile/users/seats/reports/audit reads
- Existing nine approval-gated actions
- sandbox-only organization guard
- backend-owned membership and permissions
- proposal fingerprints
- approval thresholds
- stale/version checks
- idempotent execution
- reconciliation and audit replay
- rollback proposal lineage

## New supplied source of truth

The user supplied exact column lists for eight Nucleus organization tables and
confirmed that the present implementation must remain SQLite-based with those
exact table names and no `dbo` prefix.

## Deliberate decisions

1. Exact PascalCase tables and columns are used at the ORM and migration layer.
2. Existing Workplace Agent tables are retained; this is an additive migration.
3. `OrganizationCode` maps the stable string organization ID to the integer
   `OrganizationAccountId` schema.
4. `Password` is persistence-only and excluded from every outward contract.
5. An internal sidecar supplies optimistic versions because no version columns
   were provided.
6. Company, Drug, Indication and Market access are read-only because no safe
   deactivation or delete contract was provided.
7. Category and Report access use `IsActive` rather than physical deletion.
8. OrganizationPermission updates identify one exact row by
   `OrganizationPermissionId` and require two independent approvals.
9. The existing contact-email action now synchronizes both exact-schema and
   legacy Overview state.

## Not claimed

- No real SQL Server connection is included.
- No production Nucleus API adapter is included.
- No real password or credential is included.
- No billing, session, usage or security-policy schema is inferred.
