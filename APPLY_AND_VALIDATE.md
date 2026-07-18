# Apply and validate the Nucleus organization schema slice

## Baseline

Apply this pack only to repository `shubham123dev/dem_0000_saa` after commit:

```text
1aec2a3bb08f79a8a08782596c59533e42916dfa
```

The Organization Overview vertical slice must already be committed. Do not
apply the older `organization_settings_vertical_slice_complete.zip`; this pack
supersedes it.

## 1. Verify the checkout

From the repository root:

```powershell
git branch --show-current
git rev-parse HEAD
git status --short
git remote -v
```

Expected branch: `main`.

Expected starting commit:

```text
1aec2a3bb08f79a8a08782596c59533e42916dfa
```

The only acceptable pre-existing untracked file is a transport archive that
will not be committed. Commit or remove any other local changes first.

## 2. Extract and overlay

Save `nucleus_organization_schema_vertical_slice_complete.zip` in Downloads,
then run from the repository root:

```powershell
$zip = "$env:USERPROFILE\Downloads\nucleus_organization_schema_vertical_slice_complete.zip"
$temp = "$env:TEMP\nucleus_organization_schema_apply"

Remove-Item $temp -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path $zip -DestinationPath $temp -Force

$source = Join-Path $temp "nucleus_organization_schema_vertical_slice_complete"
Copy-Item -Path "$source\*" -Destination "." -Recurse -Force

git status --short
```

The repository must remain flat. The result must be `app/...`, `alembic/...`
and `tests/...`, not a nested `nucleus_organization_schema_vertical_slice_complete`
folder.

## 3. Activate and install

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## 4. Compile, migrate and seed

```powershell
python -m compileall -q app tests alembic
alembic upgrade head
alembic current
python -m app.db.seed
python -m app.db.seed
```

Expected migration:

```text
0014_workplace_resources (head)
```

Both seed runs must complete successfully.

## 5. Run the complete suite

```powershell
pytest -q
```

Do not commit if any test fails.

## 6. Run the API

```powershell
.\.venv\Scripts\uvicorn.exe app.main:app --reload
```

Open Swagger:

```text
http://127.0.0.1:8000/docs
```

## 7. Smoke-test all new reads

In a second PowerShell window:

```powershell
$base = "http://127.0.0.1:8000"
$admin = @{ "X-Mock-User-Id" = "usr_admin_001" }
$reader = @{ "X-Mock-User-Id" = "usr_member_001" }
$org = "org_sandbox_001"

Invoke-RestMethod -Headers $admin "$base/workplace/organizations/$org/nucleus/account" |
    ConvertTo-Json -Depth 20

Invoke-RestMethod -Headers $admin "$base/workplace/organizations/$org/nucleus/license" |
    ConvertTo-Json -Depth 20

Invoke-RestMethod -Headers $admin "$base/workplace/organizations/$org/nucleus/approval-status" |
    ConvertTo-Json -Depth 20

Invoke-RestMethod -Headers $reader "$base/workplace/organizations/$org/nucleus/entitlements" |
    ConvertTo-Json -Depth 30
```

Expected seed highlights:

```text
OrganizationAccountId  1
OrganizationCode       org_sandbox_001
OrganizationName       Demo Enterprise Sandbox
OrganizationType       Enterprise
MaxUserLimit            5
LicenseEndDate          2026-11-26
CategoryID              101
CompanyID               201
DrugID                  301
IndicationID            401
MarketID                501
ReportsID               1001
ReportsCustomID         605
```

The account response must not contain `Password` or a `password` property.

## 8. Check capabilities

```powershell
Invoke-RestMethod "$base/workplace/capabilities" |
    ConvertTo-Json -Depth 20
```

Expected current surface:

```text
20 read tools
43 write actions
```

## 9. Smoke-test one controlled action

Create a dry-run account-field proposal:

```powershell
$proposal = Invoke-RestMethod `
    -Method Post `
    -Headers $admin `
    -ContentType "application/json" `
    -Uri "$base/workplace/organizations/$org/agent/actions/propose" `
    -Body (@{
        action_name = "update_nucleus_organization_account_field"
        arguments = @{
            field_name = "Industry"
            value = "Market Intelligence"
        }
    } | ConvertTo-Json -Depth 10)

$proposal | ConvertTo-Json -Depth 20
$proposalId = $proposal.proposal.id
```

Approve and execute:

```powershell
Invoke-RestMethod `
    -Method Post `
    -Headers $admin `
    -ContentType "application/json" `
    -Uri "$base/workplace/organizations/$org/agent/actions/$proposalId/approve" `
    -Body '{"reason":"Reviewed in local sandbox"}' |
    ConvertTo-Json -Depth 20

Invoke-RestMethod `
    -Method Post `
    -Headers $admin `
    -ContentType "application/json" `
    -Uri "$base/workplace/organizations/$org/agent/actions/$proposalId/execute" `
    -Body '{"idempotency_key":"nucleus-industry-local-001"}' |
    ConvertTo-Json -Depth 30
```

Re-read the account and confirm `industry` changed. Repeating execution with
the same idempotency key must return the same execution. A different key must
return an idempotency conflict.

## 10. Inspect audit and readiness

```powershell
Invoke-RestMethod -Headers $admin "$base/workplace/organizations/$org/audit-log" |
    ConvertTo-Json -Depth 30

Invoke-RestMethod "$base/ready/details" |
    ConvertTo-Json -Depth 20
```

Readiness must report migration `0013_nucleus_admin`, Nucleus administrative
sidecar support, and registry/handler parity of 38/38, plus workplace-resource runtime and permission checks.

## 11. Commit only after validation

Do not add the ZIP archive.

```powershell
git status --short
git add app alembic tests docs README.md pyproject.toml APPLY_AND_VALIDATE.md FILE_MANIFEST.md SOURCE_STATE_AUDIT.md VALIDATION_REPORT.md
git commit -m "add governed workplace resource runtime"
git push origin main
git status --short
```

After push, the working tree should be clean except for an intentionally
untracked transport archive outside the repository or excluded by `.gitignore`.
## Agent-native resource validation

After applying the agent-native resource patch, the migration head remains:

```text
0014_workplace_resources
```

Expected capability surface:

```text
16 read tools
38 write actions
38 handlers
```

Validate natural-language resource discovery and clarification through:

```powershell
$base = "http://127.0.0.1:8000"
$org = "org_sandbox_001"
$admin = @{ "X-Mock-User-Id" = "usr_admin_001" }

Invoke-RestMethod -Method Post -Headers $admin -ContentType "application/json" `
    -Uri "$base/workplace/organizations/$org/agent/query" `
    -Body '{"query":"What workplace resources can you manage?"}' |
    ConvertTo-Json -Depth 40

Invoke-RestMethod "$base/ready/details" | ConvertTo-Json -Depth 30
```

Readiness must report `read_tools.registered = 16`, exact action/handler parity
of `38/38`, `agent_resource_tools_registered = true`, and
`workplace_operation_routes_valid = true`.


## Final workplace-workflow validation

Expected migration and governed surface:

```text
0015_workplace_workflows
20 read tools
43 registered actions
43 handlers
42 model-selectable actions
```

Readiness must report `workflow_schema_supported = true`,
`workplace_workflow_permission_seeded = true`,
`internal_rollback_hidden_from_model = true`, exact `43/43` action parity and
20 registered read tools. Run the seed twice and the complete test suite before
committing.

<!-- ANGULAR_FRONTEND_PHASE_0_VALIDATION -->
## Angular frontend Phase 0 validation

```powershell
python scripts/validate_frontend_contracts.py --repo .
pytest -q tests/test_frontend_contracts.py
python -m compileall -q scripts tests
pytest -q
git diff --check
```

Expected contract surface: 31 unique public endpoint method/path pairs and 13
validated synthetic examples. No Angular runtime or fake streaming behavior is
introduced in this phase.

<!-- ANGULAR_FRONTEND_PHASE_1_VALIDATION -->
## Angular frontend Phase 1 validation

```powershell
python scripts/validate_frontend_contracts.py --repo .
python scripts/validate_angular_phase1.py --repo .
pytest -q tests/test_frontend_contracts.py tests/test_angular_phase1_foundation.py

Set-Location frontend
npm install
npm run validate:phase1
npx playwright install chromium
npm run e2e
Set-Location ..

pytest -q
git diff --check
git status --short
```

The checked-in development proxy maps `/api` to local FastAPI before browser tests.

Expected frontend foundation: Angular 21 LTS, strict standalone/zoneless
bootstrap, 31 typed API operations, functional interceptors, fail-closed runtime
validation, Vitest tests and Playwright discovery. Streaming remains unavailable
and must not be simulated.

<!-- ANGULAR_FRONTEND_PHASE_2_VALIDATION -->
## Angular frontend Phase 2 validation

```powershell
python scripts/validate_angular_phase2.py --repo .
pytest -q tests/test_angular_phase2.py
Set-Location frontend
npm run validate:phase2
npx playwright test
Set-Location ..
git diff --check
```

<!-- ANGULAR_FRONTEND_PHASE_3_VALIDATION -->
## Angular frontend Phase 3 validation

```powershell
python scripts/validate_angular_phase2.py --repo .
python scripts/validate_angular_phase3.py --repo .
pytest -q tests/test_angular_phase2.py tests/test_angular_phase3.py
Set-Location frontend
npm run validate:phase3
npm run e2e
Set-Location ..
pytest -q
git diff --check
```
