# DBMR Workplace Agent — Sandbox Backend

This repository is a separate backend for the DBMR Workplace Agent. The existing SARA/chatbot codebase remains unchanged and is not integrated here.

## Runtime model

```text
X-Mock-User-Id
→ active backend user
→ active organization membership
→ backend-owned resource permission
→ backend-owned action-management permission
→ sandbox and organization-status guard
→ one structured planner call
→ read execution or immutable action proposal
→ policy-controlled approval threshold
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
→ distinct approver decisions
→ approval threshold reached
→ fingerprint and permission revalidation
→ optimistic resource-version check
→ single-use idempotent execution
→ success, failure, stale or reconciliation-required outcome
```

Low- and medium-risk actions require one approval. High-risk role changes and member removals require two distinct approvers and disallow requester self-approval. A rejection closes the proposal immediately. All approved decisions are consumed atomically when execution starts.

Natural-language requests may create proposals but never approve or execute them.

## Action-management permissions

Lifecycle access is separate from resource authorization:

- `agent.actions.read`
- `agent.actions.approve`
- `agent.actions.execute`
- `agent.actions.reconcile`

A management permission never replaces the selected action's permission. For example, execution of a seat revocation requires both `agent.actions.execute` and `organization.seats.revoke`.

## Rollback proposals

A successful reversible action can generate a new rollback proposal:

```text
successful source action
→ inspect stored before/after result
→ build existing inverse action
→ persist rollback lineage
→ normal permission and dry-run validation
→ normal approval threshold
→ normal version-checked execution
```

Rollback never executes automatically. Unsupported or incomplete inverse operations return `agent_action_rollback_unavailable` rather than guessing prior state.

## Operational hardening

- Proposal lists use bounded cursor pagination and optional status, action and requester filters.
- Pending proposal limits apply per organization and per requester.
- Proposal rate limits apply per requester per minute.
- Reconciliation and audit replay have bounded retry counts.
- Audit replay writes only a recovery audit event; it never repeats the business mutation.
- A failed execution-start audit remains `audit_pending` after successful mutation completion until replay succeeds.
- `/ready/details` checks migration head, sandbox mode, registry/handler parity, management permissions and audit backlog without exposing secrets.
- The deterministic sandbox seed contains three independent administrators so two-person approval policies are usable immediately.

## Operational invariants

- Membership activation is allowed only from `invited` to `active`.
- Membership role changes are version checked.
- The final active organization administrator cannot be demoted or removed.
- A member with an active seat must be unseated before membership removal.
- Membership, seat and report-access history is preserved through status changes; rows are not deleted.
- Seat assignment and revocation use versioned conditional updates.
- Report grants and revocations use versioned conditional updates.
- An approved proposal whose reviewed resource changes becomes `stale` rather than producing an internal error.
- One approver can record only one decision per proposal.
- Rollback lineage is immutable and links source and rollback proposals.

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

The current migration head is `0009_operational_hardening`. The deterministic seed is idempotent and does not call `create_all()`.

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
| GET | `/ready` | Database connectivity readiness |
| GET | `/ready/details` | Release-readiness details without secrets |
| GET | `/workplace/capabilities` | Read tools, action catalogue and approval policies |
| POST | `/workplace/organizations/{organization_id}/agent/query` | Read plan or dry-run action proposal |
| POST | `/workplace/organizations/{organization_id}/agent/actions/propose` | Explicit dry-run proposal |
| GET | `/workplace/organizations/{organization_id}/agent/actions` | Bounded cursor-paginated proposal list |
| GET | `/workplace/organizations/{organization_id}/agent/actions/{proposal_id}` | Read a proposal |
| POST | `/workplace/organizations/{organization_id}/agent/actions/{proposal_id}/approve` | Record one approver decision |
| POST | `/workplace/organizations/{organization_id}/agent/actions/{proposal_id}/reject` | Reject and close proposal |
| POST | `/workplace/organizations/{organization_id}/agent/actions/{proposal_id}/cancel` | Cancel pending/approved proposal |
| POST | `/workplace/organizations/{organization_id}/agent/actions/{proposal_id}/rollback-proposal` | Create a separately approved inverse proposal |
| POST | `/workplace/organizations/{organization_id}/agent/actions/{proposal_id}/execute` | Single-use threshold-gated execution |
| POST | `/workplace/organizations/{organization_id}/agent/actions/{proposal_id}/reconcile` | Inspect uncertain outcome |
| POST | `/workplace/organizations/{organization_id}/agent/actions/{proposal_id}/audit-replay` | Retry audit persistence only |

All organization endpoints require `X-Mock-User-Id` except health, readiness and capabilities.

## Validation

```bash
python -m compileall -q app tests alembic
alembic upgrade head
python -m app.db.seed
pytest -q
```

The GitHub Actions workflow runs on `main`, pull requests and manual `workflow_dispatch`, across Python 3.11 and 3.12. Tests use isolated temporary SQLite databases with foreign-key enforcement enabled.
