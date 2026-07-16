# Organization API Contracts

Step 0 exposes read-only workplace operations backed by `OrganizationApiGateway`. No write operation is implemented.

## Common authorization

Every organization-scoped endpoint requires:

- `X-Mock-User-Id` resolving to an active user
- an active membership in the requested organization
- the operation's backend-owned permission
- an organization whose environment is `sandbox`

Roles and permissions are loaded from the database. Request text cannot grant access.

## Implemented adapter methods

```python
async def get_profile(organization_id: str) -> OrganizationProfile
async def list_members(organization_id: str) -> list[OrganizationMember]
async def get_seat_summary(organization_id: str) -> SeatSummary
async def list_reports(organization_id: str) -> list[ReportWithAccess]
async def check_report_access(
    organization_id: str,
    report_id: str,
) -> ReportAccessDecision
```

## Implemented HTTP endpoints

| Method | Endpoint | Required permission |
|---|---|---|
| GET | `/workplace/organizations/{organization_id}/profile` | `organization.profile.read` |
| GET | `/workplace/organizations/{organization_id}/users` | `organization.users.read` |
| GET | `/workplace/organizations/{organization_id}/seats` | `organization.seats.read` |
| GET | `/workplace/organizations/{organization_id}/reports` | `organization.reports.read` |
| GET | `/workplace/organizations/{organization_id}/reports/{report_id}/access` | `organization.reports.read` |
| GET | `/workplace/organizations/{organization_id}/audit-log` | `audit.read` |

## Verification and audit

- Responses are built from exact backend state returned by the gateway.
- Each successful business read appends an organization-scoped audit event.
- Audit-log reads are not audited to prevent unbounded self-referential events.
- Reads are non-mutating, so rollback is not applicable.

## Error behavior

| HTTP | Error code | Meaning |
|---|---|---|
| 401 | `unauthenticated` | missing or unknown user identity |
| 403 | `user_disabled` | user account is disabled |
| 403 | `organization_access_denied` | no active membership |
| 403 | `permission_denied` | membership role lacks required permission |
| 403 | `production_access_blocked` | organization is not sandbox |
| 404 | `organization_not_found` | organization does not exist |
| 500 | `internal_error` | unexpected failure without internal detail leakage |

## Future writes

Any future write contract must use the controlled sequence:

```text
inspect → propose immutable action → approve → execute → re-read → verify → audit → rollback
```

No provisional write endpoint is exposed in Step 0.
