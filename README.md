# DBMR Workplace Agent — Sandbox Backend

This repository is a separate backend for the DBMR Workplace Agent. The existing SARA/chatbot codebase remains unchanged and is not integrated here.

## Runtime model

```text
X-Mock-User-Id
→ active backend user
→ active organization membership
→ backend-owned permission check
→ sandbox and organization-status guard
→ one structured planner call
→ read execution or immutable action proposal
→ explicit approval
→ version-checked execution
→ verification, audit and reconciliation
```

Production organizations are blocked. Model output cannot provide organization scope, actor identity, permissions, approval state, proposal IDs, execution commands or idempotency keys.

## Read capabilities

- `get_organization_profile`
- `list_organization_users`
- `get_organization_seat_summary`
- `list_organization_reports`
- `check_organization_report_access`
- `get_organization_audit_log`

## Approval-gated actions

- `update_organization_contact_email`
- `invite_organization_user`
- `activate_organization_membership`
- `update_organization_member_role`
- `remove_organization_user`
- `assign_organization_seat`
- `revoke_organization_seat`
- `grant_organization_report_access`
- `revoke_organization_report_access`

Every action follows the same backend-owned lifecycle:

```text
dry-run proposal
→ immutable reviewed change set
→ explicit approval or rejection
→ fingerprint and permission revalidation
→ optimistic resource-version check
→ single-use idempotent execution
→ success, failure, stale or reconciliation-required outcome
```

Natural-language requests may create proposals but never approve or execute them.

## Operational invariants

- Membership activation is allowed only from `invited` to `active`.
- Membership role changes are version checked.
- The final active organization administrator cannot be demoted or removed.
- A member with an active seat must be unseated before membership removal.
- Membership, seat and report-access history is preserved through status changes; rows are not deleted.
- Seat assignment and revocation use versioned conditional updates.
- Report grants and revocations use versioned conditional updates.
- An approved proposal whose reviewed resource changes becomes `stale` rather than producing an internal error.

## Guardrails

- Sandbox only; production access is denied.
- No arbitrary SQL, arbitrary URL/HTTP, shell or browser tool.
- No frontend code.
- No production credentials or real employee data.
- Permissions are loaded from backend role data.
- Approval policy is owned by the action registry.
- Concurrent approval and execution transitions use conditional database updates.
- Successful mutations are not reversed when audit persistence fails.
- Uncertain outcomes are reconciled by inspection without repeating an unapproved mutation.

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

The current migration head is `0007_complete_inverse_lifecycle`. The deterministic seed is idempotent and does not call `create_all()`.

## Run

```bash
uvicorn app.main:app --reload
```

The raw mock Nucleus API is disabled by default. Enable it only for isolated sandbox contract testing:

```env
WORKPLACE_ENABLE_RAW_MOCK_API=true
```

## Main endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness |
| GET | `/ready` | Database readiness |
| GET | `/workplace/capabilities` | Read tools and action catalogue |
| POST | `/workplace/organizations/{organization_id}/agent/query` | Read plan or dry-run action proposal |
| POST | `/workplace/organizations/{organization_id}/agent/actions/propose` | Explicit dry-run proposal |
| GET | `/workplace/organizations/{organization_id}/agent/actions` | List proposals |
| GET | `/workplace/organizations/{organization_id}/agent/actions/{proposal_id}` | Read a proposal |
| POST | `/workplace/organizations/{organization_id}/agent/actions/{proposal_id}/approve` | Explicit approval |
| POST | `/workplace/organizations/{organization_id}/agent/actions/{proposal_id}/reject` | Explicit rejection |
| POST | `/workplace/organizations/{organization_id}/agent/actions/{proposal_id}/cancel` | Cancel pending/approved proposal |
| POST | `/workplace/organizations/{organization_id}/agent/actions/{proposal_id}/execute` | Single-use execution |
| POST | `/workplace/organizations/{organization_id}/agent/actions/{proposal_id}/reconcile` | Inspect uncertain outcome |

All organization endpoints require `X-Mock-User-Id` except health, readiness and capabilities.

## Validation

```bash
python -m compileall -q app tests alembic
alembic upgrade head
python -m app.db.seed
pytest -q
```

Tests use isolated temporary SQLite databases with foreign-key enforcement enabled.
