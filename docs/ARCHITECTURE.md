# Architecture (Step 0)

## Request flow

```
Frontend Workplace tab
        │
        ▼
Workplace Agent backend (FastAPI)
        │
        ▼
Authentication / organization context     (X-Mock-Employee-Id → Employee)
        │
        ▼
Permission service                         (backend-owned roles & permissions)
        │
        ▼
Organization adapter contract              (OrganizationGateway protocol)
        │
        ▼
Mock organization API / database           (MockOrganizationAdapter → SQLite)
        │
        ▼
Audit log                                  (append-only audit_events)
```

Every read of an organization profile records an append-only audit event.

## Layered design

| Layer | Responsibility | Touches ORM? |
| ----- | -------------- | ------------ |
| `app/api` | HTTP routes, request dependencies, auth resolution | No |
| `app/services` | Orchestration of the read flow | No |
| `app/permissions` | Backend-owned authorization | No (via repo) |
| `app/adapters/organization` | Replaceable gateway to the org system of record | No (via repo) |
| `app/repositories` | Only components that use SQLAlchemy directly | **Yes** |
| `app/db` | Engine/session, ORM models, seed | Yes |
| `app/domain` | Enums + framework-agnostic domain models | No |
| `app/schemas` | Pydantic request/response contracts | No |

The service and API layers depend on the **adapter contract**
(`OrganizationGateway`), never on the SQLite ORM.

## Adapter replacement plan

The adapter is the seam that lets the mock database be replaced by the real
Nucleus organization API without changing services or routes:

```
MockOrganizationAdapter          (Step 0 — backed by mock SQLite database)
        │
        ▼  (future replacement, same OrganizationGateway contract)
NucleusOrganizationApiAdapter    (NOT implemented in Step 0)
```

Both implementations satisfy:

```python
async def get_profile(organization_id: str) -> OrganizationProfile
```

## Persistence

Five mock tables (see `docs/ORGANIZATION_API_CONTRACTS.md` and the ORM models):
`organizations`, `employees`, `employee_organization_roles`,
`role_permissions`, `audit_events`.

Schema is managed by Alembic (`alembic upgrade head`) and populated by an
idempotent seed (`python -m app.db.seed`).
