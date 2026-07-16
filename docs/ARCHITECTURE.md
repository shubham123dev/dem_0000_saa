# Architecture (Step 0)

## Request flow

```text
Frontend Workplace tab
→ FastAPI Workplace backend
→ X-Mock-User-Id authentication
→ active organization membership
→ backend-owned permission check
→ sandbox-only organization guard
→ OrganizationApiGateway
→ MockOrganizationApiAdapter
→ MockOrganizationApi
→ repositories
→ SQLite sandbox database
→ append-only audit log
```

The protected Workplace surface is `/workplace/organizations/...`.

The optional raw mock system-of-record surface is `/mock-api/v1/...`. It is disabled by default and mounted only when both conditions are true:

- `WORKPLACE_ENVIRONMENT=sandbox`
- `WORKPLACE_ENABLE_RAW_MOCK_API=true`

## Layers

| Layer | Responsibility | ORM access |
|---|---|---|
| `app/api` | HTTP contracts and dependency wiring | No |
| `app/services` | sandbox checks, authorization orchestration and audit | No |
| `app/permissions` | active membership and database-owned permission checks | Through repository |
| `app/adapters/organization` | replaceable organization-system contract | No |
| `app/mock_api` | mock Nucleus system-of-record behavior | Through repositories |
| `app/repositories` | SQLAlchemy persistence queries | Yes |
| `app/db` | engine, sessions, migrations and deterministic seed | Yes |
| `app/domain` | framework-independent domain models | No |
| `app/schemas` | Pydantic API contracts | No |

## Replaceable adapters

```text
MockOrganizationApiAdapter
→ future replacement with NucleusOrganizationApiAdapter

MockChatbotGateway (defined but not wired)
→ future replacement with SaraChatbotApiGateway
```

The Workplace service depends on `OrganizationApiGateway`, not SQLite or ORM models.

## Persistent model

The sandbox database contains nine tables:

1. `organizations`
2. `users`
3. `organization_memberships`
4. `organization_seat_pools`
5. `seat_assignments`
6. `reports`
7. `organization_report_access`
8. `role_permissions`
9. `audit_events`

Users and seats are distinct. Seat use is calculated from active assignments. Report access belongs to the organization.

## Schema lifecycle

Alembic is the application schema authority:

```bash
alembic upgrade head
python -m app.db.seed
```

The seed does not call `create_all()`. Tests may create isolated temporary schemas directly and enable SQLite foreign-key enforcement.

## Step 0 boundary

Step 0 contains only read tools. It has no LLM planner, write execution, approval workflow, arbitrary SQL/HTTP, shell access, browser automation or production integration.
