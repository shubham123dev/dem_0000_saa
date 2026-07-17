# Agent Tool Contracts

The Workplace Agent exposes a fixed allowlist. It has no arbitrary SQL, shell, browser control or unrestricted HTTP execution.

| Tool | Permission | Model-supplied input | Output |
|---|---|---|---|
| `get_organization_overview` | `organization.profile.read` | none | stable overview contract |
| `get_organization_profile` | `organization.profile.read` | none | organization profile |
| `list_organization_users` | `organization.users.read` | none | organization members |
| `get_organization_seat_summary` | `organization.seats.read` | none | calculated seat summary |
| `list_organization_reports` | `organization.reports.read` | none | report catalogue with access |
| `check_organization_report_access` | `organization.reports.read` | `report_id` | exact access decision |
| `get_organization_audit_log` | `audit.read` | none | organization audit events |

Organization ID, user identity, roles and permissions come only from trusted backend request context. They are forbidden in model-generated tool arguments.

## Overview questions now supported

- Show my organization overview.
- What is our workspace health?
- How many modules are licensed?
- How many areas are available?
- When is the renewal date?
- How many organization logins are configured?

## Write boundary

Natural-language changes can create only dry-run proposals. Approval and execution remain separate explicit backend calls. The nine action types continue to use the existing proposal, approval, idempotency, verification, audit, reconciliation and rollback controls.

## Failure cases

| HTTP | Error code | When |
|---|---|---|
| 401 | `unauthenticated` | missing or unknown identity |
| 403 | `user_disabled` | disabled user |
| 403 | `organization_access_denied` | no active membership |
| 403 | `permission_denied` | role lacks permission |
| 403 | `production_access_blocked` | non-sandbox organization |
| 404 | `organization_not_found` | organization absent |
| 422 | `agent_tool_call_invalid` | unknown tool, extra arguments or model-supplied identity |
| 500 | `internal_error` | unexpected failure |
