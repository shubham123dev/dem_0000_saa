# Agent tool contracts

The Workplace Agent exposes a fixed backend allowlist. It does not expose
arbitrary SQL, shell, browser control or unrestricted HTTP execution.

## Read tools

| Tool | Permission | Model arguments | Result |
|---|---|---|---|
| `get_organization_overview` | `organization.profile.read` | none | Overview card contract |
| `get_nucleus_organization_account` | `organization.account.read` | none | Exact OrganizationAccount state without Password |
| `get_nucleus_organization_license` | `organization.account.read` | none | MaxUserLimit and licence dates/status |
| `get_nucleus_organization_approval_status` | `organization.account.read` | none | approval/rejection state |
| `get_nucleus_organization_entitlements` | `organization.entitlements.read` | none | all supplied access and permission rows |
| `get_organization_profile` | `organization.profile.read` | none | legacy stable profile |
| `list_organization_users` | `organization.users.read` | none | organization members |
| `get_organization_seat_summary` | `organization.seats.read` | none | calculated seat summary |
| `list_organization_reports` | `organization.reports.read` | none | legacy report catalogue/access |
| `check_organization_report_access` | `organization.reports.read` | `report_id` | exact legacy report decision |
| `get_organization_audit_log` | `audit.read` | none | audit events |

Organization scope, actor identity, roles and permissions are injected from
trusted request context and are forbidden in model arguments.

## Write proposal tools

The planner may propose only registry-defined actions. The Nucleus additions
are:

- `update_nucleus_organization_account_field(field_name, value)`
- `clear_nucleus_organization_account_field(field_name)`
- `grant_nucleus_category_access(category_id, category_sample_id)`
- `revoke_nucleus_category_access(access_id)`
- `grant_nucleus_report_access(reports_id, sample_id, sample_toc_id, speciality_id, executive_access)`
- `revoke_nucleus_report_access(access_id)`
- `update_nucleus_organization_permissions(permission_id, six resource IDs, is_active)`

Use the literal string `null` for nullable numeric/Boolean action arguments.
`permission_id=null` creates a new OrganizationPermission row; a numeric ID
updates that exact organization-owned row.

A model can create only a dry-run proposal. Approval, rejection, execution,
idempotency keys, reconciliation and rollback remain separate backend-owned
operations.
