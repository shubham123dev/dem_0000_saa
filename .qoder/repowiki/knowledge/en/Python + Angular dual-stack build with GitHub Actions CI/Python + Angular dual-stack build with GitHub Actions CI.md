---
kind: build_system
name: Python + Angular dual-stack build with GitHub Actions CI
category: build_system
scope:
    - '**'
source_files:
    - pyproject.toml
    - alembic.ini
    - .github/workflows/tests.yml
    - frontend/package.json
---

The repository is a dual-stack project (FastAPI backend + Angular frontend) built and validated through a lightweight, script-driven pipeline with no containerization or Makefile. Build and validation are orchestrated by pyproject.toml, frontend/package.json, and a single GitHub Actions workflow.

Backend (Python)
- Package: dbmr-workplace-agent declared in pyproject.toml; uses setuptools.build_meta as the build backend and installs via pip install -e ".[dev]".
- Runtime deps: FastAPI, Uvicorn, Pydantic v2, SQLAlchemy 2.x, Alembic, aioodbc/pyodbc for SQL Server, aiosqlite for sandbox/dev, httpx.
- Dev extras: pytest, pytest-asyncio, anyio.
- Test discovery: tests/ directory, asyncio auto-mode, -q output.
- Database migrations: Alembic configured via alembic.ini (script_location = alembic, default URL points to sqlite:///./workplace_sandbox.db). Migrations live under alembic/versions/ and are applied with python -m alembic upgrade head.
- App entry point is app/main.py; database seeding is invoked via python -m app.db.seed.

Frontend (Angular)
- Package: dbmr-workplace-agent-ui under frontend/package.json; Node engine pinned to ^20.19 || ^22.12 || ^24.0, npm >= 10.
- Scripts: ng serve (dev server on port 4201 with proxy), ng build, typecheck via three tsconfigs (tsconfig.app.json, tsconfig.spec.json, tsconfig.e2e.json), ESLint, unit tests via ng test, E2E via Playwright.
- Phase-gated validation scripts (validate:phase1..6) chain architecture-boundary checks, typecheck, lint, unit tests, build, and e2e listing; validate:full runs phase6 plus full e2e suite.
- E2E browsers installed via npx playwright install --with-deps chromium.

CI (GitHub Actions — .github/workflows/tests.yml)
- Triggered on push/PR to main and via workflow_dispatch; concurrency group cancels in-progress runs per ref.
- Two parallel jobs:
  - backend: matrix over Python 3.11 / 3.12, installs editable package with dev extras, compiles bytecode of app, tests, alembic, scripts, validates frontend contracts and phase scripts, upgrades Alembic twice, seeds DB twice, then runs pytest -q. Test output is uploaded as artifacts.
  - frontend: Node 22.13, npm ci with lockfile caching, installs Playwright Chromium, runs npm run validate:phase6, then npm run e2e. Uploads validation log, Playwright report, traces, and screenshots on failure.
- No Docker images, no release/publish steps, no artifact packaging beyond logs/reports.

Conventions & constraints
- Backend must be installed in editable mode before running tests/migrations.
- Frontend builds require Node within the engines range; use npm ci for reproducible installs.
- Database schema changes go through Alembic migrations under alembic/versions/; CI verifies idempotent double-upgrade and double-seed.
- Frontend contract validation scripts under scripts/ are part of the CI backend job, ensuring backend/frontend wire contracts stay in sync.