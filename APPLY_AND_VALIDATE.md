# Apply and validate the Organization Overview vertical slice

This pack contains complete replacement/new files relative to repository commit:

```text
e0e93cfb2a7192cb221210ba87125f5898bab734
```

## Apply

Copy the pack contents over the repository root while preserving directories. New files are:

```text
alembic/versions/0010_add_organization_overview.py
app/repositories/organization_overview_repository.py
tests/test_organization_overview.py
```

All other files in the pack are full replacements.

## Fresh local validation

Windows PowerShell:

```powershell
cd dem_0000_saa
py -3.12 -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
Copy-Item .env.example .env -Force
python -m compileall -q app tests alembic
alembic upgrade head
alembic current
python -m app.db.seed
pytest -q
```

Expected migration head:

```text
0010_add_organization_overview (head)
```

Run the API:

```powershell
uvicorn app.main:app --reload
```

## Manual endpoint checks

```powershell
$base = "http://127.0.0.1:8000"
$admin = @{ "X-Mock-User-Id" = "usr_admin_001" }

Invoke-RestMethod `
  -Headers $admin `
  "$base/workplace/organizations/org_sandbox_001/overview" |
  ConvertTo-Json -Depth 10
```

Expected overview metrics:

```text
licensed_modules          2
available_areas           9
organization_logins       1
workspace_health_percent  98
renewal_date               2026-11-26
workspace_status           healthy
```

## Chat check

Configure the model environment values, then call:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Headers $admin `
  -ContentType "application/json" `
  -Body '{"query":"Show my organization overview and workspace health"}' `
  "$base/workplace/organizations/org_sandbox_001/agent/query" |
  ConvertTo-Json -Depth 20
```

The planner must choose `get_organization_overview`; organization scope and identity must not appear in model arguments.

## Approval-gated change check

1. Propose `update_organization_contact_email`.
2. Approve or reject through the existing action endpoint.
3. Execute an approved proposal with a unique idempotency key.
4. Re-read `/overview`.
5. Confirm approved execution changes the contact email and increments the organization version.
6. Confirm rejected execution changes nothing.
7. Confirm `organization.overview.read` and action lifecycle events appear in the audit log.

## Important

The pack was statically syntax-checked in the artifact environment. Full repository tests must be run after applying it because the GitHub repository could not be cloned into that isolated environment.
