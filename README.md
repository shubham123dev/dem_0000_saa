# DBMR Workplace Agent — Step 0

This repository is a separate, sandbox-only backend foundation for the future DBMR Workplace Agent. The existing SARA/chatbot repository remains unchanged and is not integrated in Step 0.

## What Step 0 proves

```text
X-Mock-User-Id
→ active mock user
→ active organization membership
→ backend-owned permission check
→ sandbox organization guard
→ OrganizationApiGateway
→ MockOrganizationApiAdapter
→ SQLite mock database
→ append-only audit event
```

Step 0 exposes five read-only workplace capabilities:

- `get_organization_profile`
- `list_organization_users`
- `get_organization_seat_summary`
- `list_organization_reports`
- `check_organization_report_access`

It deliberately contains no LLM planner, write action, approval execution, arbitrary SQL, arbitrary HTTP, shell tool, browser automation, production credential, or frontend code.

## Domain model

The mock sandbox persists nine tables:

1. `organizations`
2. `users`
3. `organization_memberships`
4. `organization_seat_pools`
5. `seat_assignments`
6. `reports`
7. `organization_report_access`
8. `role_permissions`
9. `audit_events`

Users and seats are separate. An organization may have any number of members, while only selected users consume licensed seats. Report access belongs to the organization and is resolved by backend data.

## Setup

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS/Linux
source .venv/bin/activate

pip install -e ".[dev]"
copy .env.example .env   # Windows
# cp .env.example .env  # macOS/Linux
```

## Database

Alembic is the only application schema authority:

```bash
alembic upgrade head
python -m app.db.seed
```

The seed is deterministic and idempotent. It does not call `create_all()`.

Seeded data includes one sandbox organization, six synthetic users, five memberships, five licensed seats, three active seat assignments, five reports and three organization report grants.

## Run

```bash
uvicorn app.main:app --reload
```

The raw mock Nucleus API is disabled by default. Enable it only for isolated local contract testing:

```env
WORKPLACE_ENABLE_RAW_MOCK_API=true
```

## Main endpoints

| Method | Path | Auth |
|---|---|---|
| GET | `/health` | none |
| GET | `/ready` | none |
| GET | `/workplace/capabilities` | none |
| GET | `/workplace/organizations/{organization_id}/profile` | `X-Mock-User-Id` |
| GET | `/workplace/organizations/{organization_id}/users` | `X-Mock-User-Id` |
| GET | `/workplace/organizations/{organization_id}/seats` | `X-Mock-User-Id` |
| GET | `/workplace/organizations/{organization_id}/reports` | `X-Mock-User-Id` |
| GET | `/workplace/organizations/{organization_id}/reports/{report_id}/access` | `X-Mock-User-Id` |
| GET | `/workplace/organizations/{organization_id}/audit-log` | `X-Mock-User-Id` |

No workplace `POST`, `PUT`, `PATCH` or `DELETE` route exists in Step 0.

## Example

```bash
curl -H "X-Mock-User-Id: usr_admin_001" \
  http://127.0.0.1:8000/workplace/organizations/org_sandbox_001/profile
```

## Tests

```bash
python -m compileall -q app tests
pytest -q
```

Tests use isolated temporary SQLite databases with foreign-key enforcement enabled.

## Next phase

The first write phase is intentionally not implemented yet:

```text
inspect → propose immutable action → approve → execute → re-read → verify → audit → rollback
```
