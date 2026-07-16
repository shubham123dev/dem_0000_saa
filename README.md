# DBMR Workplace Agent — Step 0 (Contract-First Read-Only Sandbox)

This is a **new, separate backend repository** for the DBMR Workplace Agent.

> The existing SARA/chatbot repository is completely out of scope. This service
> does not modify it, copy its pipelines, integrate with `/ai-search_1`, change
> chatbot behavior, create frontend code, or connect to production systems.

Step 0 delivers a **contract-first, production-structured, read-only sandbox
foundation**. It proves exactly one flow and nothing more:

```
Mock internal employee
→ authenticated mock context (X-Mock-Employee-Id)
→ sandbox organization selected
→ employee permission checked
→ organization profile read from mock database
→ exact state returned
→ read event recorded in audit log
```

Step 0 intentionally **does not** implement LLM planning, write actions, approval
flows, browser automation, arbitrary SQL/HTTP tools, or production integration.

## Technology

- Python + FastAPI
- Pydantic v2
- SQLAlchemy 2.x (async) with SQLite + `aiosqlite`
- Alembic migrations
- pytest / pytest-asyncio / httpx

## Project layout

```
app/          FastAPI app, domain, schemas, db, repositories, permissions, adapters, services
alembic/      Migration environment + versions
docs/         Requirements, architecture, contracts, security model
tests/        pytest suite (isolated temporary databases)
```

## Setup

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

pip install -e ".[dev]"

cp .env.example .env          # copy env (Windows: copy .env.example .env)
```

## Database: migrate + seed

```bash
alembic upgrade head
python -m app.db.seed
```

The seed is **idempotent** — running it twice produces no duplicate data.

Seeded synthetic data:

- Organization `org_sandbox_001` (Demo Enterprise Sandbox, environment `sandbox`)
- `emp_admin_001` — role `sandbox_admin`
- `emp_reader_001` — role `sandbox_reader`
- `emp_outsider_001` — no role in `org_sandbox_001`

## Run

```bash
uvicorn app.main:app --reload
```

## Step 0 endpoints

| Method | Path | Auth | Notes |
| ------ | ---- | ---- | ----- |
| GET | `/health` | none | liveness |
| GET | `/ready` | none | database connectivity |
| GET | `/workplace/capabilities` | none | one read tool, zero write tools |
| GET | `/sandbox/organizations/{organization_id}/profile` | `X-Mock-Employee-Id` | read profile + audit |
| GET | `/sandbox/organizations/{organization_id}/audit-log` | `X-Mock-Employee-Id` | append-only events |

No `POST`/`PATCH`/`PUT`/`DELETE` organization routes exist in Step 0.

## Sample requests

Authorized read:

```bash
curl -H "X-Mock-Employee-Id: emp_admin_001" \
  http://127.0.0.1:8000/sandbox/organizations/org_sandbox_001/profile
```

Unauthorized read (no membership → 403):

```bash
curl -H "X-Mock-Employee-Id: emp_outsider_001" \
  http://127.0.0.1:8000/sandbox/organizations/org_sandbox_001/profile
```

## Tests

```bash
pytest -q
```

Tests use isolated temporary databases and never touch a developer's local
SQLite file.

## Documentation

- [`docs/WORKPLACE_REQUIREMENTS.md`](docs/WORKPLACE_REQUIREMENTS.md)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/ORGANIZATION_API_CONTRACTS.md`](docs/ORGANIZATION_API_CONTRACTS.md)
- [`docs/AGENT_TOOL_CONTRACTS.md`](docs/AGENT_TOOL_CONTRACTS.md)
- [`docs/SECURITY_MODEL.md`](docs/SECURITY_MODEL.md)

## Scope boundary

This foundation stops after Step 0. The next step (not implemented here) will
introduce the first controlled write workflow: inspect → propose immutable
action → approve → update → re-read → verify → audit → rollback.
