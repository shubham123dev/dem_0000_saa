# Agent Tool Contracts

The Workplace Agent exposes a small fixed set of read-only tools. There is no arbitrary SQL, shell, browser control or unrestricted HTTP execution.

| Tool | Permission | Input | Output |
|---|---|---|---|
| `get_organization_profile` | `organization.profile.read` | `organization_id` | organization profile |
| `list_organization_users` | `organization.users.read` | `organization_id` | organization members |
| `get_organization_seat_summary` | `organization.seats.read` | `organization_id` | calculated seat summary |
| `list_organization_reports` | `organization.reports.read` | `organization_id` | report catalog with access annotations |
| `check_organization_report_access` | `organization.reports.read` | `organization_id`, `report_id` | exact access decision |

All tools are sandbox-only and backed by `OrganizationApiGateway`. They authenticate with `X-Mock-User-Id`, authorize against database-owned membership and permission data, and append audit events for successful business reads.

## Failure cases

| HTTP | Error code | When |
|---|---|---|
| 401 | `unauthenticated` | missing or unknown user identity |
| 403 | `user_disabled` | user account is disabled |
| 403 | `organization_access_denied` | user lacks active organization membership |
| 403 | `permission_denied` | membership role lacks the required permission |
| 403 | `production_access_blocked` | organization is not sandbox |
| 404 | `organization_not_found` | organization does not exist |
| 500 | `internal_error` | unexpected failure |

## Write boundary

Step 0 registers no write tools and exposes no workplace `POST`, `PUT`, `PATCH` or `DELETE` routes. Future writes must follow explicit proposal, approval, verification, audit and rollback controls.

## Testing boundary

Runtime code under `app/` contains production-facing contracts and sandbox adapters only. Test doubles, fake planners, fixtures and deterministic model responses must be placed under `tests/`.
