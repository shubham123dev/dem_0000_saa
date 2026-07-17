# Architecture

## Repository boundary

This repository contains the standalone Workplace Agent backend and an isolated Angular demonstration workspace. The existing SARA/chatbot system remains in a different repository. Backend authorization is never delegated to frontend code.

## Read request flow

```text
Workplace client or chat
        ↓
FastAPI route / agent query
        ↓
X-Mock-User-Id → active User
        ↓
active organization membership
        ↓
backend-owned permission
        ↓
sandbox and organization-status guard
        ↓
OrganizationApiGateway
        ↓
MockOrganizationApiAdapter → repositories → SQLite
        ↓
stable domain/API contract
        ↓
append-only audit event
```

`get_organization_overview` is the first complete page-level contract. The dashboard and chat receive the same exact backend state.

## Action request flow

```text
natural-language or explicit request
        ↓
allowlisted action registry
        ↓
resource authorization
        ↓
immutable dry-run proposal
        ↓
one- or two-person approval policy
        ↓
fingerprint, permission and version revalidation
        ↓
idempotent execution
        ↓
re-read/verification
        ↓
audit, reconciliation or rollback proposal
```

## Layered design

| Layer | Responsibility | Touches ORM? |
|---|---|---|
| `app/api` | HTTP routes, dependencies and identity resolution | No |
| `app/agent` | Allowlisted planning, tool execution and grounded synthesis | No |
| `app/services` | Read and action orchestration | No |
| `app/permissions` | Backend-owned authorization | Via repository |
| `app/adapters/organization` | Replaceable system-of-record gateway | No |
| `app/repositories` | Persistence queries and conditional transitions | Yes |
| `app/db` | Engine, sessions, ORM models and deterministic seed | Yes |
| `app/domain` | Framework-neutral enums and models | No |
| `app/schemas` | Stable HTTP contracts | No |
| `tests` | Isolated verification and test doubles | Test-only |

## Adapter replacement

```text
MockOrganizationApiAdapter       current sandbox implementation
        │
        └── same OrganizationApiGateway contract
                │
                ▼
NucleusOrganizationApiAdapter    future real implementation
```

The gateway covers overview, profile, members, seat summary, report listing, report-access checks and versioned contact-email updates. A future real adapter translates raw Nucleus responses into these domain models; it does not leak raw provider schemas into the agent or frontend.

## Persistence

The application schema has 14 tables:

1. `organizations`
2. `organization_overviews`
3. `users`
4. `organization_memberships`
5. `organization_seat_pools`
6. `seat_assignments`
7. `reports`
8. `organization_report_access`
9. `role_permissions`
10. `audit_events`
11. `agent_action_proposals`
12. `agent_action_approvals`
13. `agent_action_executions`
14. `agent_action_rollbacks`

Alembic is the schema authority. The expected head is `0010_add_organization_overview`.
