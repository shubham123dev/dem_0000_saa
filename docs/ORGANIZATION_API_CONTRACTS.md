# Organization API Contracts

## Common authorization

Every organization-scoped Workplace endpoint requires:

- `X-Mock-User-Id` resolving to an active user;
- an active membership in the requested organization;
- the operation's backend-owned permission;
- an active sandbox organization.

Roles and permissions come from database state. Request text cannot grant access.

## Stable overview contract

`GET /workplace/organizations/{organization_id}/overview`

Permission: `organization.profile.read`

```json
{
  "organization": {
    "id": "org_sandbox_001",
    "display_name": "Demo Enterprise Sandbox",
    "legal_name": "Demo Enterprise Private Limited",
    "contact_email": "operations@example.test",
    "environment": "sandbox",
    "status": "active",
    "version": 1,
    "organization_type": "organization",
    "renewal_date": "2026-11-26",
    "workspace_status": "healthy"
  },
  "metrics": {
    "licensed_modules": 2,
    "available_areas": 9,
    "organization_logins": 1,
    "workspace_health_percent": 98
  },
  "overview_version": 1,
  "overview_updated_at": "2026-01-01T00:00:00Z",
  "access": {
    "user_id": "usr_admin_001",
    "permission": "organization.profile.read"
  },
  "generated_at": "2026-07-18T00:00:00Z"
}
```

The raw mock system-of-record endpoint returns the same overview data without Workplace `access` or `generated_at` fields:

`GET /mock-api/v1/organizations/{organization_id}/overview`

## Gateway methods

```python
async def get_profile(organization_id: str) -> OrganizationProfile
async def get_overview(organization_id: str) -> OrganizationOverview
async def list_members(organization_id: str) -> list[OrganizationMember]
async def get_seat_summary(organization_id: str) -> SeatSummary
async def list_reports(organization_id: str) -> list[ReportWithAccess]
async def check_report_access(
    organization_id: str,
    report_id: str,
) -> ReportAccessDecision
async def update_contact_email(
    organization_id: str,
    contact_email: str,
) -> OrganizationProfile
async def update_contact_email_if_version(
    organization_id: str,
    contact_email: str,
    expected_version: int,
) -> OrganizationProfile | None
```

## Workplace endpoints

| Method | Endpoint | Permission |
|---|---|---|
| GET | `/workplace/organizations/{organization_id}/overview` | `organization.profile.read` |
| GET | `/workplace/organizations/{organization_id}/profile` | `organization.profile.read` |
| GET | `/workplace/organizations/{organization_id}/users` | `organization.users.read` |
| GET | `/workplace/organizations/{organization_id}/seats` | `organization.seats.read` |
| GET | `/workplace/organizations/{organization_id}/reports` | `organization.reports.read` |
| GET | `/workplace/organizations/{organization_id}/reports/{report_id}/access` | `organization.reports.read` |
| GET | `/workplace/organizations/{organization_id}/audit-log` | `audit.read` |

## Verification and audit

- Successful overview reads append `organization.overview.read`.
- Overview values come from backend state, never Angular constants.
- Approved contact-email execution is visible in the next overview read.
- Rejected or stale proposals cannot alter the overview.
- Audit-log reads are not audited to prevent self-referential growth.

## Error behavior

| HTTP | Error code | Meaning |
|---|---|---|
| 401 | `unauthenticated` | missing or unknown user identity |
| 403 | `user_disabled` | user account is disabled |
| 403 | `organization_access_denied` | no active membership |
| 403 | `permission_denied` | role lacks required permission |
| 403 | `production_access_blocked` | organization is not sandbox |
| 403 | `organization_suspended` | organization is inactive |
| 404 | `organization_not_found` | organization does not exist |
| 500 | `internal_error` | unexpected failure without internal leakage |
