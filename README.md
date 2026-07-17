# DBMR Workplace Agent — Sandbox Backend

This repository is a standalone sandbox backend for the DBMR Workplace Agent. It exposes permission-enforced organization reads and approval-gated administrative actions while keeping the existing SARA/chatbot repository unchanged.

## Runtime model

```text
X-Mock-User-Id
→ active backend user
→ active organization membership
→ backend-owned resource permission
→ backend-owned action-management permission
→ sandbox and organization-status guard
→ one structured planner call
→ authorized read execution or immutable action proposal
→ policy-controlled approval threshold
→ version-checked execution
→ verification, audit, reconciliation and optional rollback proposal
```

Production organizations are blocked. Model output cannot provide organization scope, actor identity, permissions, approval state, proposal IDs, execution commands or idempotency keys.

## Read capabilities

- `get_organization_overview`
- `get_organization_profile`
- `list_organization_users`
- `get_organization_seat_summary`
- `list_organization_reports`
- `check_organization_report_access`
- `get_organization_audit_log`

The overview contract is the stable backend surface for the Nucleus Overview page. It contains organization identity, renewal date, workspace status, licensed modules, available areas, organization login count and workspace health. The frontend and chat consume the same contract.

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

Low- and medium-risk actions require one approval. High-risk role changes and member removals require two distinct approvers and disallow requester self-approval. A rejection closes the proposal immediately. Natural-language requests can create proposals but cannot approve or execute them.

## Overview vertical slice

```text
GET /workplace/organizations/{organization_id}/overview
→ organization.profile.read authorization
→ stable OrganizationOverview response
→ append-only organization.overview.read audit event
```

The existing contact-email action completes the first Cloudflare-style demonstration:

```text
read overview
→ propose contact-email change
→ approve or reject
→ execute once
→ re-read overview
→ verify exact before/after state
→ inspect audit history
```

## Adapter boundary

```text
Workplace routes and agent tools
        ↓
OrganizationApiGateway
        ├── MockOrganizationApiAdapter       current sandbox
        └── NucleusOrganizationApiAdapter    future real integration
```

The future Nucleus adapter maps its real wire schema into the stable domain contracts. Frontend and agent code do not depend on raw Nucleus field names.

## Database

Alembic is the only schema authority. The current migration head is:

```text
0010_add_organization_overview
```

The sandbox has 14 application tables: the original organization/user/seat/report/audit tables, four action-lifecycle tables and `organization_overviews`.

```bash
alembic upgrade head
python -m app.db.seed
```

The seed is deterministic and idempotent. It contains one sandbox organization, a complete overview record, three administrators, three active reader members, one invited member, one outsider, five seats, three active assignments, five reports and three report grants.

## Setup

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
Copy-Item .env.example .env
```

macOS/Linux:

```bash
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
cp .env.example .env
```

## Run

```bash
uvicorn app.main:app --reload
```

Enable the unauthenticated raw mock system-of-record routes only for isolated local contract testing:

```env
WORKPLACE_ENABLE_RAW_MOCK_API=true
```

## Main endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness |
| GET | `/ready` | Database connectivity |
| GET | `/ready/details` | Release-readiness checks without secrets |
| GET | `/workplace/capabilities` | Read tools, action catalogue and approval policies |
| GET | `/workplace/organizations/{organization_id}/overview` | Complete Overview page contract |
| GET | `/workplace/organizations/{organization_id}/profile` | Organization profile |
| GET | `/workplace/organizations/{organization_id}/users` | Users and memberships |
| GET | `/workplace/organizations/{organization_id}/seats` | Seat summary |
| GET | `/workplace/organizations/{organization_id}/reports` | Reports with organization access |
| GET | `/workplace/organizations/{organization_id}/reports/{report_id}/access` | Exact report-access decision |
| GET | `/workplace/organizations/{organization_id}/audit-log` | Organization audit log |
| POST | `/workplace/organizations/{organization_id}/agent/query` | Natural-language read or dry-run proposal |
| POST | `/workplace/organizations/{organization_id}/agent/actions/propose` | Explicit dry-run proposal |
| GET | `/workplace/organizations/{organization_id}/agent/actions` | Bounded proposal list |
| GET | `/workplace/organizations/{organization_id}/agent/actions/{proposal_id}` | Read a proposal |
| POST | `/workplace/organizations/{organization_id}/agent/actions/{proposal_id}/approve` | Record approval |
| POST | `/workplace/organizations/{organization_id}/agent/actions/{proposal_id}/reject` | Reject proposal |
| POST | `/workplace/organizations/{organization_id}/agent/actions/{proposal_id}/cancel` | Cancel proposal |
| POST | `/workplace/organizations/{organization_id}/agent/actions/{proposal_id}/execute` | Threshold-gated execution |
| POST | `/workplace/organizations/{organization_id}/agent/actions/{proposal_id}/reconcile` | Inspect uncertain outcome |
| POST | `/workplace/organizations/{organization_id}/agent/actions/{proposal_id}/rollback-proposal` | Prepare inverse proposal |
| POST | `/workplace/organizations/{organization_id}/agent/actions/{proposal_id}/audit-replay` | Retry audit persistence only |

All organization-scoped Workplace endpoints require `X-Mock-User-Id`.

## Validation

```bash
python -m compileall -q app tests alembic
alembic upgrade head
python -m app.db.seed
pytest -q
```

The GitHub Actions workflow should run the same backend validation on Python 3.11 and 3.12. Tests use isolated temporary SQLite databases with foreign-key enforcement enabled.
