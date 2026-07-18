# Nucleus SQLite schema mapping

The SQLite mock preserves the supplied PascalCase table and column names.
Python attributes and API fields use snake_case only above the persistence
boundary.

## OrganizationAccount

| SQLite column | Stable field | Exposure |
|---|---|---|
| OrganizationAccountId | organization_account_id | Admin read |
| OrganizationName | organization_name | Admin read, approval-gated update |
| OrganizationCode | organization_code | Admin read, protected from chat writes |
| OrganizationType | organization_type | Admin read, approval-gated update/clear |
| Industry | industry | Admin read, approval-gated update/clear |
| Website | website | Admin read, approval-gated update/clear |
| UserName | login_username | Admin read only |
| Password | none | Never exposed |
| Email | email | Admin read, approval-gated update/clear |
| ContactPersonName | contact_person_name | Admin read, approval-gated update/clear |
| ContactPersonDesignation | contact_person_designation | Admin read, approval-gated update/clear |
| ContactPhone | contact_phone | Admin read, approval-gated update/clear |
| AddressLine1 | address_line1 | Admin read, approval-gated update/clear |
| AddressLine2 | address_line2 | Admin read, approval-gated update/clear |
| City | city | Admin read, approval-gated update/clear |
| State | state | Admin read, approval-gated update/clear |
| Country | country | Admin read, approval-gated update/clear |
| PostalCode | postal_code | Admin read, approval-gated update/clear |
| MaxUserLimit | max_user_limit | Admin licence read only |
| LicenseStartDate | license_start_date | Admin licence read only |
| LicenseEndDate | license_end_date | Admin licence read only |
| Status and approval columns | approval status | Admin read only |
| IsActive | is_active | Admin read only |
| Created/Updated columns | audit metadata | Admin read only |

## Entitlement tables

- `OrganizationCategoryAccess`: read; `IsActive` grant/revoke supported.
- `OrganizationCompanyProfileAccess`: read-only because no lifecycle/delete field was supplied.
- `OrganizationDrugAccess`: read-only because no lifecycle/delete field was supplied.
- `OrganizationIndicationAccess`: read-only because no lifecycle/delete field was supplied.
- `OrganizationMarketAccess`: read-only because no lifecycle/delete field was supplied.
- `OrganizationReportAccess`: read; `IsActive` grant/revoke supported.
- `OrganizationPermission`: read; exact-row create/update/deactivate supported with two-person approval.

## Organization identity mapping

The existing Workplace path identifier `org_sandbox_001` maps to
`OrganizationAccount.OrganizationCode`. The synthetic seed uses
`OrganizationAccountId = 1`.

## Version sidecar

The supplied schema contains no resource-version columns. The internal
`nucleus_resource_versions` table provides optimistic concurrency without
altering the supplied table definitions. It is not part of a future external
Nucleus API contract.
