# Backend API contract baseline

Baseline commit: `1863fc0ec62b148dc1976c154afa1f91e3375c16`  
Contract version: `0.1.0`

This document records the HTTP surface that exists before Angular implementation. It is derived from the registered FastAPI routers and Pydantic response models. It is not a proposal for new endpoints.

## Browser boundary

- Organization-scoped routes require `X-Mock-User-Id` in the sandbox.
- Angular components must never construct that header. A single authentication interceptor will own it.
- `X-Request-Id` may be supplied by the browser and is always returned by the backend.
- Errors use `{"error": {"code", "message", "request_id"}}`.
- The browser must not calculate risk, approvals, organization scope, resource versions, or execution steps.

## Current public surface

The machine-readable source is `frontend/contracts/api-manifest.json`. It contains 31 endpoints and is checked against `create_app().openapi()`.

### Health and discovery

| Method | Path | Auth | Response |
|---|---|---:|---|
| GET | `/health` | No | Liveness object |
| GET | `/ready` | No | Readiness object |
| GET | `/ready/details` | No | Detailed readiness object |
| GET | `/workplace/capabilities` | No | `CapabilitiesResponse` |

### Organization and Nucleus reads

| Method | Path | Response |
|---|---|---|
| GET | `/workplace/organizations/{organization_id}/overview` | `OrganizationOverviewResponse` |
| GET | `/workplace/organizations/{organization_id}/profile` | `OrganizationProfileResponse` |
| GET | `/workplace/organizations/{organization_id}/users` | `OrganizationUsersResponse` |
| GET | `/workplace/organizations/{organization_id}/seats` | `OrganizationSeatsResponse` |
| GET | `/workplace/organizations/{organization_id}/reports` | `OrganizationReportsResponse` |
| GET | `/workplace/organizations/{organization_id}/reports/{report_id}/access` | `ReportAccessResponse` |
| GET | `/workplace/organizations/{organization_id}/audit-log` | `AuditLogResponse` |
| GET | `/workplace/organizations/{organization_id}/nucleus/account` | `NucleusAccountResponse` |
| GET | `/workplace/organizations/{organization_id}/nucleus/license` | `NucleusLicenseResponse` |
| GET | `/workplace/organizations/{organization_id}/nucleus/approval-status` | `NucleusApprovalStatusResponse` |
| GET | `/workplace/organizations/{organization_id}/nucleus/entitlements` | `NucleusEntitlementsResponse` |

### Generic resource reads

| Method | Path | Request | Response |
|---|---|---|---|
| GET | `/workplace/organizations/{organization_id}/resources` | — | `WorkplaceResourceTypeListResponse` |
| GET | `/workplace/organizations/{organization_id}/resources/{resource_type}/schema` | — | `WorkplaceResourceSchemaResponse` |
| POST | `/workplace/organizations/{organization_id}/resources/{resource_type}/search` | `WorkplaceResourceSearchRequest` | `WorkplaceResourceSearchResponse` |
| POST | `/workplace/organizations/{organization_id}/resources/{resource_type}/count` | `WorkplaceResourceSearchRequest` | `WorkplaceResourceCountResponse` |
| GET | `/workplace/organizations/{organization_id}/resources/{resource_type}/{resource_id}` | — | `WorkplaceResourceResponse` |

### Natural-language agent

`POST /workplace/organizations/{organization_id}/agent/query`

Request:

```json
{"query": "Onboard reader@example.test as a reader with a standard seat"}
```

The response is one of three modes:

- `read`: answer plus evidence/tool results.
- `clarification_required`: answer plus non-empty `missing_fields` and no execution payload.
- `action_proposal`: answer plus a dry-run proposal summary and no read evidence.

### Governed action lifecycle

| Method | Path | Request | Response |
|---|---|---|---|
| POST | `.../agent/actions/propose` | `AgentActionProposalRequest` | `AgentActionProposalResponse` |
| GET | `.../agent/actions` | Query filters | `AgentActionProposalListResponse` |
| GET | `.../agent/actions/{proposal_id}` | — | `AgentActionProposalResponse` |
| POST | `.../agent/actions/{proposal_id}/approve` | `AgentActionDecisionRequest` | `AgentActionApprovalResponse` |
| POST | `.../agent/actions/{proposal_id}/reject` | `AgentActionDecisionRequest` | `AgentActionApprovalResponse` |
| POST | `.../agent/actions/{proposal_id}/cancel` | `AgentActionDecisionRequest` | `AgentActionProposalResponse` |
| POST | `.../agent/actions/{proposal_id}/rollback-proposal` | `AgentActionDecisionRequest` | `AgentActionProposalResponse` |
| POST | `.../agent/actions/{proposal_id}/execute` | `AgentActionExecutionRequest` | `AgentActionExecutionResponse` |
| POST | `.../agent/actions/{proposal_id}/reconcile` | — | `AgentActionExecutionResponse` |
| POST | `.../agent/actions/{proposal_id}/audit-replay` | — | `AgentActionExecutionResponse` |

## Lifecycle invariants

1. Proposal creation is dry-run only.
2. The backend freezes arguments, changes, resource versions, risk and approval policy.
3. Approval decisions are actor-derived by the backend.
4. Execution requires a caller-generated idempotency key.
5. Stale or expired proposals are not executable.
6. Reconciliation is distinct from success and failure.
7. Rollback is a new high-risk proposal, never a local UI undo.
8. The internal snapshot restore action is not model-selectable.

## Validation

```bash
python scripts/validate_frontend_contracts.py --repo .
pytest -q tests/test_frontend_contracts.py
```
