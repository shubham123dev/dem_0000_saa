# Architecture (Step 0)

## Repository boundary

This repository contains only the standalone Workplace Agent backend. The existing SARA/chatbot system remains in a different repository and is not referenced by runtime code here. Test doubles and fixtures belong under `tests/`.

## Request flow

```text
Workplace client
        │
        ▼
FastAPI workplace route
        │
        ▼
X-Mock-User-Id → active User
        │
        ▼
Active organization membership
        │
        ▼
Backend-owned role and permission check
        │
        ▼
Sandbox-only organization guard
        │
        ▼
OrganizationApiGateway
        │
        ▼
MockOrganizationApiAdapter → repositories → SQLite
        │
        ▼
Append-only audit event
```

Each successful workplace tool read records an audit event, except reading the audit log itself to avoid self-referential growth.

## Layered design

| Layer | Responsibility | Touches ORM? |
|---|---|---|
| `app/api` | HTTP routes, dependencies and identity resolution | No |
| `app/services` | Read-tool orchestration | No |
| `app/permissions` | Backend-owned authorization | No, via repository |
| `app/adapters/organization` | Replaceable organization-system gateway | No, via repositories |
| `app/repositories` | SQLAlchemy persistence queries | Yes |
| `app/db` | Engine, sessions, ORM models and seed | Yes |
| `app/domain` | Framework-neutral enums and domain models | No |
| `app/schemas` | Pydantic HTTP contracts | No |
| `tests` | Fixtures, test doubles and automated verification | Test-only |

The service and API layers depend on `OrganizationApiGateway`, never directly on SQLite ORM objects.

## Adapter replacement plan

```text
MockOrganizationApiAdapter       current sandbox implementation
        │
        ▼ same OrganizationApiGateway contract
NucleusOrganizationApiAdapter    future implementation, not present in Step 0
```

The gateway covers organization profile, members, seat summary, report listing and report-access checks.

## Persistence

The sandbox schema contains nine tables:

1. `organizations`
2. `users`
3. `organization_memberships`
4. `organization_seat_pools`
5. `seat_assignments`
6. `reports`
7. `organization_report_access`
8. `role_permissions`
9. `audit_events`

Alembic is the schema authority. `python -m app.db.seed` populates deterministic synthetic sandbox data after migration.
