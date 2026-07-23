# Action Control & Governance Models

<cite>
**Referenced Files in This Document**
- [action_control_models.py](file://app/db/action_control_models.py)
- [action_control_repository.py](file://app/repositories/action_control_repository.py)
- [action_control_service.py](file://app/services/action_control_service.py)
- [hardened_agent_action_repository.py](file://app/repositories/hardened_agent_action_repository.py)
- [multi_approval_agent_action_repository.py](file://app/repositories/multi_approval_agent_action_repository.py)
- [hardened_agent_action_service.py](file://app/services/hardened_agent_action_service.py)
- [agent_action_reconciliation_service.py](file://app/services/agent_action_reconciliation_service.py)
- [action_control_routes.py](file://app/api/action_control_routes.py)
- [action_control_dependencies.py](file://app/api/action_control_dependencies.py)
- [action_contracts.py](file://app/agent/action_contracts.py)
- [action_control_contracts.py](file://app/agent/action_control_contracts.py)
- [action_state.py](file://app/agent/action_state.py)
- [audit_repository.py](file://app/repositories/audit_repository.py)
- [0017_governed_action_control_plane.py](file://alembic/versions/0017_governed_action_control_plane.py)
- [0008_add_multi_approval_and_rollbacks.py](file://alembic/versions/0008_add_multi_approval_and_rollbacks.py)
- [0005_harden_agent_action_lifecycle.py](file://alembic/versions/0005_harden_agent_action_lifecycle.py)
- [GOVERNED_ACTION_CONTROL_PLANE.md](file://docs/GOVERNED_ACTION_CONTROL_PLANE.md)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)
10. [Appendices](#appendices)

## Introduction
This document describes the data model and control-plane design for governed actions, including proposal workflows, approval hierarchies, audit trails, rollback mechanisms, hardened execution, multi-approval systems, and compensation actions. It explains state transitions, security boundaries, compliance requirements, and integration between action models and the governance framework. It also provides examples of complex approval workflows, audit query patterns, and reconciliation processes.

## Project Structure
The governed action control plane spans database models, repositories, services, API routes, contracts, and migrations:

```mermaid
graph TB
subgraph "API Layer"
R["Action Control Routes"]
D["Dependencies"]
end
subgraph "Services"
S["Action Control Service"]
HS["Hardened Agent Action Service"]
RS["Agent Action Reconciliation Service"]
end
subgraph "Repositories"
AR["Action Control Repository"]
HAR["Hardened Agent Action Repository"]
MAR["Multi-Approval Agent Action Repository"]
AUD["Audit Repository"]
end
subgraph "Domain/Contracts"
AC["Action Contracts"]
ACC["Action Control Contracts"]
AS["Action State"]
end
subgraph "Persistence"
DBM["DB Models (Action Control)"]
MIG1["Migration: Governed Action Control Plane"]
MIG2["Migration: Multi-Approval & Rollbacks"]
MIG3["Migration: Harden Lifecycle"]
end
R --> S
D --> S
S --> AR
S --> HAR
S --> MAR
S --> AUD
HS --> HAR
RS --> AR
AR --> DBM
HAR --> DBM
MAR --> DBM
AUD --> DBM
DBM --> MIG1
DBM --> MIG2
DBM --> MIG3
S --> AC
S --> ACC
S --> AS
```

**Diagram sources**
- [action_control_routes.py](file://app/api/action_control_routes.py)
- [action_control_dependencies.py](file://app/api/action_control_dependencies.py)
- [action_control_service.py](file://app/services/action_control_service.py)
- [hardened_agent_action_service.py](file://app/services/hardened_agent_action_service.py)
- [agent_action_reconciliation_service.py](file://app/services/agent_action_reconciliation_service.py)
- [action_control_repository.py](file://app/repositories/action_control_repository.py)
- [hardened_agent_action_repository.py](file://app/repositories/hardened_agent_action_repository.py)
- [multi_approval_agent_action_repository.py](file://app/repositories/multi_approval_agent_action_repository.py)
- [audit_repository.py](file://app/repositories/audit_repository.py)
- [action_contracts.py](file://app/agent/action_contracts.py)
- [action_control_contracts.py](file://app/agent/action_control_contracts.py)
- [action_state.py](file://app/agent/action_state.py)
- [action_control_models.py](file://app/db/action_control_models.py)
- [0017_governed_action_control_plane.py](file://alembic/versions/0017_governed_action_control_plane.py)
- [0008_add_multi_approval_and_rollbacks.py](file://alembic/versions/0008_add_multi_approval_and_rollbacks.py)
- [0005_harden_agent_action_lifecycle.py](file://alembic/versions/0005_harden_agent_action_lifecycle.py)

**Section sources**
- [GOVERNED_ACTION_CONTROL_PLANE.md](file://docs/GOVERNED_ACTION_CONTROL_PLANE.md)

## Core Components
- Data models define the entities for proposals, approvals, audit events, rollbacks, and compensation actions.
- Repositories encapsulate persistence and enforce invariants such as idempotency, ordering, and authorization checks.
- Services orchestrate workflows across repositories, apply policies, and emit audit events.
- API routes expose controlled endpoints with dependency injection for services and repositories.
- Contracts define request/response shapes and event schemas used by clients and integrations.

Key responsibilities:
- Proposal lifecycle management and validation
- Multi-approval policy evaluation and enforcement
- Hardened execution with preconditions and post-execution verification
- Audit trail capture and querying
- Rollback and compensation action handling
- Reconciliation between intended and actual outcomes

**Section sources**
- [action_control_models.py](file://app/db/action_control_models.py)
- [action_control_repository.py](file://app/repositories/action_control_repository.py)
- [action_control_service.py](file://app/services/action_control_service.py)
- [hardened_agent_action_repository.py](file://app/repositories/hardened_agent_action_repository.py)
- [multi_approval_agent_action_repository.py](file://app/repositories/multi_approval_agent_action_repository.py)
- [hardened_agent_action_service.py](file://app/services/hardened_agent_action_service.py)
- [agent_action_reconciliation_service.py](file://app/services/agent_action_reconciliation_service.py)
- [action_contracts.py](file://app/agent/action_contracts.py)
- [action_control_contracts.py](file://app/agent/action_control_contracts.py)
- [action_state.py](file://app/agent/action_state.py)
- [audit_repository.py](file://app/repositories/audit_repository.py)

## Architecture Overview
The governed action control plane enforces a strict separation between intent (proposal), policy (approvals), execution (hardened), and evidence (audit). The flow is designed to be auditable, reversible where possible, and resilient to partial failures via compensation.

```mermaid
sequenceDiagram
participant Client as "Client"
participant API as "Action Control Routes"
participant Svc as "Action Control Service"
participant Repo as "Action Control Repository"
participant HRepo as "Hardened Agent Action Repository"
participant MRepo as "Multi-Approval Repository"
participant Aud as "Audit Repository"
Client->>API : "Create Proposal"
API->>Svc : "create_proposal(...)"
Svc->>Repo : "persist proposal"
Svc->>Aud : "emit audit event"
Svc-->>API : "Proposal created"
API-->>Client : "Proposal ID"
Client->>API : "Approve Proposal"
API->>Svc : "submit_approval(...)"
Svc->>MRepo : "record approval"
Svc->>Svc : "evaluate policy"
alt "Policy satisfied"
Svc->>HRepo : "execute hardened action"
HRepo-->>Svc : "execution result"
Svc->>Aud : "emit execution audit"
Svc-->>API : "Execution succeeded"
else "Policy not satisfied"
Svc-->>API : "Await more approvals"
end
API-->>Client : "Status update"
```

**Diagram sources**
- [action_control_routes.py](file://app/api/action_control_routes.py)
- [action_control_service.py](file://app/services/action_control_service.py)
- [action_control_repository.py](file://app/repositories/action_control_repository.py)
- [hardened_agent_action_repository.py](file://app/repositories/hardened_agent_action_repository.py)
- [multi_approval_agent_action_repository.py](file://app/repositories/multi_approval_agent_action_repository.py)
- [audit_repository.py](file://app/repositories/audit_repository.py)

## Detailed Component Analysis

### Data Model Entities
The core entities include:
- Proposal: Captures intent, target resource, operation type, parameters, and metadata.
- Approval: Records approver identity, timestamp, decision, and rationale; supports multiple approvers and hierarchical rules.
- Audit Event: Immutable record of lifecycle transitions, decisions, and execution results.
- Rollback/Compensation Action: Inverse operations or compensations triggered on failure or policy violation.
- Execution Context: Pre/post conditions, environment bindings, and outcome verification artifacts.

These entities are persisted through the action control models and enforced by repository constraints.

```mermaid
erDiagram
PROPOSAL {
uuid id PK
string organization_id
string actor_id
string operation_type
jsonb parameters
enum status
timestamp created_at
timestamp updated_at
}
APPROVAL {
uuid id PK
uuid proposal_id FK
string approver_id
enum decision
text rationale
timestamp approved_at
}
AUDIT_EVENT {
uuid id PK
uuid proposal_id FK
string event_type
jsonb payload
timestamp occurred_at
}
COMPENSATION_ACTION {
uuid id PK
uuid proposal_id FK
string inverse_operation
jsonb compensation_params
enum status
timestamp created_at
}
PROPOSAL ||--o{ APPROVAL : "has many"
PROPOSAL ||--o{ AUDIT_EVENT : "generates"
PROPOSAL ||--o{ COMPENSATION_ACTION : "may trigger"
```

**Diagram sources**
- [action_control_models.py](file://app/db/action_control_models.py)
- [0017_governed_action_control_plane.py](file://alembic/versions/0017_governed_action_control_plane.py)
- [0008_add_multi_approval_and_rollbacks.py](file://alembic/versions/0008_add_multi_approval_and_rollbacks.py)
- [0005_harden_agent_action_lifecycle.py](file://alembic/versions/0005_harden_agent_action_lifecycle.py)

**Section sources**
- [action_control_models.py](file://app/db/action_control_models.py)
- [0017_governed_action_control_plane.py](file://alembic/versions/0017_governed_action_control_plane.py)
- [0008_add_multi_approval_and_rollbacks.py](file://alembic/versions/0008_add_multi_approval_and_rollbacks.py)
- [0005_harden_agent_action_lifecycle.py](file://alembic/versions/0005_harden_agent_action_lifecycle.py)

### Proposal Workflow and State Transitions
Proposals follow a deterministic lifecycle:
- Draft -> Pending Approval -> Approved -> Executing -> Completed | Failed
- On failure or policy violation, proposals may transition to Compensation Required and then to Compensated or Rolled Back.

State transitions are guarded by repository-level checks and service-level policy evaluation.

```mermaid
stateDiagram-v2
[*] --> Draft
Draft --> PendingApproval : "Submit"
PendingApproval --> Approved : "All required approvals granted"
PendingApproval --> Draft : "Withdrawn"
Approved --> Executing : "Execute hardened action"
Executing --> Completed : "Post-checks pass"
Executing --> Failed : "Precondition/postcondition fail"
Failed --> CompensationRequired : "Trigger compensation"
CompensationRequired --> Compensated : "Compensation succeeds"
CompensationRequired --> RolledBack : "Rollback succeeds"
Compensated --> [*]
RolledBack --> [*]
```

**Diagram sources**
- [action_state.py](file://app/agent/action_state.py)
- [action_control_service.py](file://app/services/action_control_service.py)
- [hardened_agent_action_repository.py](file://app/repositories/hardened_agent_action_repository.py)

**Section sources**
- [action_state.py](file://app/agent/action_state.py)
- [action_control_service.py](file://app/services/action_control_service.py)
- [hardened_agent_action_repository.py](file://app/repositories/hardened_agent_action_repository.py)

### Multi-Approval System and Hierarchies
- Multiple approvers can be required per proposal based on policy.
- Approvals are recorded with identity, decision, and rationale.
- Policy evaluation aggregates approvals and enforces hierarchy (e.g., role-based thresholds).
- The multi-approval repository ensures atomic recording and consistent aggregation.

```mermaid
flowchart TD
Start(["Submit Approval"]) --> Record["Record Approval"]
Record --> Aggregate["Aggregate Approvals"]
Aggregate --> CheckPolicy{"Policy Satisfied?"}
CheckPolicy --> |Yes| Proceed["Proceed to Execution"]
CheckPolicy --> |No| Await["Await More Approvals"]
Proceed --> End(["Transition to Approved"])
Await --> End
```

**Diagram sources**
- [multi_approval_agent_action_repository.py](file://app/repositories/multi_approval_agent_action_repository.py)
- [action_control_service.py](file://app/services/action_control_service.py)

**Section sources**
- [multi_approval_agent_action_repository.py](file://app/repositories/multi_approval_agent_action_repository.py)
- [action_control_service.py](file://app/services/action_control_service.py)

### Hardened Action Execution Model
Hardened execution enforces:
- Preconditions validation before execution
- Idempotent execution with deduplication keys
- Post-execution verification against expected outcomes
- Automatic compensation if verification fails

```mermaid
sequenceDiagram
participant Svc as "Hardened Agent Action Service"
participant Repo as "Hardened Agent Action Repository"
participant Aud as "Audit Repository"
Svc->>Repo : "validate_preconditions(proposal)"
Repo-->>Svc : "preconditions ok"
Svc->>Repo : "execute_hardened(proposal, idempotency_key)"
Repo-->>Svc : "execution_result"
Svc->>Repo : "verify_postconditions(proposal, execution_result)"
alt "Verification passes"
Svc->>Aud : "emit execution_success"
Svc-->>Svc : "transition to Completed"
else "Verification fails"
Svc->>Aud : "emit execution_failure"
Svc-->>Svc : "transition to Failed"
end
```

**Diagram sources**
- [hardened_agent_action_service.py](file://app/services/hardened_agent_action_service.py)
- [hardened_agent_action_repository.py](file://app/repositories/hardened_agent_action_repository.py)
- [audit_repository.py](file://app/repositories/audit_repository.py)

**Section sources**
- [hardened_agent_action_service.py](file://app/services/hardened_agent_action_service.py)
- [hardened_agent_action_repository.py](file://app/repositories/hardened_agent_action_repository.py)
- [audit_repository.py](file://app/repositories/audit_repository.py)

### Audit Trails and Query Patterns
Audit events are immutable and cover:
- Proposal creation and updates
- Approval submissions and decisions
- Execution attempts and outcomes
- Compensation triggers and results

Common query patterns:
- Filter by proposal ID and event type
- Time-bounded queries for compliance windows
- Aggregations by approver or operation type
- Joining audit events with proposal metadata for reporting

```mermaid
flowchart TD
QStart(["Audit Query"]) --> SelectScope["Select Scope<br/>by proposal_id, time_range, event_types"]
SelectScope --> FetchEvents["Fetch Events from Audit Repository"]
FetchEvents --> Enrich["Enrich with Proposal Metadata"]
Enrich --> Output["Return Ordered Audit Timeline"]
```

**Diagram sources**
- [audit_repository.py](file://app/repositories/audit_repository.py)
- [action_control_repository.py](file://app/repositories/action_control_repository.py)

**Section sources**
- [audit_repository.py](file://app/repositories/audit_repository.py)
- [action_control_repository.py](file://app/repositories/action_control_repository.py)

### Rollback and Compensation Actions
- Compensation actions are defined as inverse operations tied to proposals.
- They are triggered automatically on failure or manually upon policy review.
- Compensation lifecycle mirrors proposal lifecycle with its own state transitions and audit trail.

```mermaid
flowchart TD
Trigger(["Failure Detected"]) --> Decide["Decide Compensation Strategy"]
Decide --> CreateComp["Create Compensation Action"]
CreateComp --> ExecuteComp["Execute Compensation"]
ExecuteComp --> VerifyComp{"Verification Pass?"}
VerifyComp --> |Yes| MarkCompensated["Mark Compensated"]
VerifyComp --> |No| RetryOrEscalate["Retry or Escalate"]
MarkCompensated --> End(["Closed"])
RetryOrEscalate --> End
```

**Diagram sources**
- [action_control_models.py](file://app/db/action_control_models.py)
- [action_control_service.py](file://app/services/action_control_service.py)

**Section sources**
- [action_control_models.py](file://app/db/action_control_models.py)
- [action_control_service.py](file://app/services/action_control_service.py)

### Reconciliation Processes
Reconciliation compares intended state (from proposals and approvals) with actual state (from execution results and external systems):
- Detects drift and inconsistencies
- Triggers corrective actions or escalations
- Produces reports for compliance and auditing

```mermaid
sequenceDiagram
participant RS as "Reconciliation Service"
participant AR as "Action Control Repository"
participant HR as "Hardened Agent Action Repository"
participant Aud as "Audit Repository"
RS->>AR : "List pending reconciliations"
AR-->>RS : "Proposals needing verification"
RS->>HR : "Fetch execution outcomes"
HR-->>RS : "Outcomes"
RS->>RS : "Compare intended vs actual"
alt "Drift detected"
RS->>Aud : "Emit reconciliation_alert"
RS->>AR : "Create corrective proposal"
else "Consistent"
RS->>Aud : "Emit reconciliation_ok"
end
```

**Diagram sources**
- [agent_action_reconciliation_service.py](file://app/services/agent_action_reconciliation_service.py)
- [action_control_repository.py](file://app/repositories/action_control_repository.py)
- [hardened_agent_action_repository.py](file://app/repositories/hardened_agent_action_repository.py)
- [audit_repository.py](file://app/repositories/audit_repository.py)

**Section sources**
- [agent_action_reconciliation_service.py](file://app/services/agent_action_reconciliation_service.py)
- [action_control_repository.py](file://app/repositories/action_control_repository.py)
- [hardened_agent_action_repository.py](file://app/repositories/hardened_agent_action_repository.py)
- [audit_repository.py](file://app/repositories/audit_repository.py)

### Security Boundaries and Compliance Requirements
- Authorization checks at API and service layers ensure only permitted actors can propose, approve, or execute.
- Proposals are scoped to organizations and actors; cross-boundary access is denied.
- Audit events provide tamper-evident records for compliance audits.
- Policies enforce minimum approvals, role-based thresholds, and operational constraints.

Integration points:
- Contracts define secure request/response envelopes and event schemas.
- Dependencies inject authenticated context into services and repositories.

**Section sources**
- [action_control_routes.py](file://app/api/action_control_routes.py)
- [action_control_dependencies.py](file://app/api/action_control_dependencies.py)
- [action_contracts.py](file://app/agent/action_contracts.py)
- [action_control_contracts.py](file://app/agent/action_control_contracts.py)

## Dependency Analysis
The following diagram shows key dependencies among components:

```mermaid
graph LR
Routes["Action Control Routes"] --> Svc["Action Control Service"]
Svc --> Repo["Action Control Repository"]
Svc --> HRepo["Hardened Agent Action Repository"]
Svc --> MRepo["Multi-Approval Repository"]
Svc --> Aud["Audit Repository"]
Svc --> Contracts["Action Contracts"]
Svc --> ControlContracts["Action Control Contracts"]
Svc --> State["Action State"]
Repo --> Models["DB Models"]
HRepo --> Models
MRepo --> Models
Aud --> Models
```

**Diagram sources**
- [action_control_routes.py](file://app/api/action_control_routes.py)
- [action_control_service.py](file://app/services/action_control_service.py)
- [action_control_repository.py](file://app/repositories/action_control_repository.py)
- [hardened_agent_action_repository.py](file://app/repositories/hardened_agent_action_repository.py)
- [multi_approval_agent_action_repository.py](file://app/repositories/multi_approval_agent_action_repository.py)
- [audit_repository.py](file://app/repositories/audit_repository.py)
- [action_contracts.py](file://app/agent/action_contracts.py)
- [action_control_contracts.py](file://app/agent/action_control_contracts.py)
- [action_state.py](file://app/agent/action_state.py)
- [action_control_models.py](file://app/db/action_control_models.py)

**Section sources**
- [action_control_routes.py](file://app/api/action_control_routes.py)
- [action_control_service.py](file://app/services/action_control_service.py)
- [action_control_repository.py](file://app/repositories/action_control_repository.py)
- [hardened_agent_action_repository.py](file://app/repositories/hardened_agent_action_repository.py)
- [multi_approval_agent_action_repository.py](file://app/repositories/multi_approval_agent_action_repository.py)
- [audit_repository.py](file://app/repositories/audit_repository.py)
- [action_contracts.py](file://app/agent/action_contracts.py)
- [action_control_contracts.py](file://app/agent/action_control_contracts.py)
- [action_state.py](file://app/agent/action_state.py)
- [action_control_models.py](file://app/db/action_control_models.py)

## Performance Considerations
- Use idempotency keys to prevent duplicate executions under concurrency.
- Batch audit event writes where appropriate to reduce I/O overhead.
- Index audit events by proposal_id and occurred_at for efficient queries.
- Apply optimistic locking or version fields on proposals to avoid lost updates.
- Cache policy evaluation results when safe to improve throughput.

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
Common issues and resolutions:
- Missing approvals: Ensure all required approvers have submitted decisions; check policy thresholds.
- Execution failures: Review audit events for precondition/postcondition violations; verify environment bindings.
- Compensation loops: Inspect compensation action states and outcomes; escalate if repeated failures occur.
- Reconciliation drift: Investigate discrepancies between intended and actual states; create corrective proposals.

Operational tips:
- Use audit timeline queries to reconstruct sequences around failures.
- Validate idempotency keys to detect duplicates.
- Monitor policy satisfaction metrics to identify bottlenecks.

**Section sources**
- [audit_repository.py](file://app/repositories/audit_repository.py)
- [action_control_service.py](file://app/services/action_control_service.py)
- [hardened_agent_action_service.py](file://app/services/hardened_agent_action_service.py)

## Conclusion
The governed action control plane provides a robust foundation for proposal-driven operations with strong auditability, multi-approval enforcement, hardened execution, and compensation capabilities. Its layered architecture separates concerns across API, services, repositories, and persistence, enabling clear security boundaries and compliance support. By leveraging audit trails and reconciliation processes, organizations can maintain trust and integrity in automated actions.

[No sources needed since this section summarizes without analyzing specific files]

## Appendices

### Example Complex Approval Workflows
- Cross-functional approvals requiring both technical and business sign-offs.
- Escalation paths when initial approvers are unavailable.
- Conditional approvals based on risk scores or resource sensitivity.

[No sources needed since this section doesn't analyze specific files]

### Integration Between Action Models and Governance Framework
- Contracts define wire formats and event schemas consumed by governance tools.
- Dependencies inject authenticated context and policy evaluators into services.
- Migrations evolve schema to support new governance features without breaking existing flows.

**Section sources**
- [action_contracts.py](file://app/agent/action_contracts.py)
- [action_control_contracts.py](file://app/agent/action_control_contracts.py)
- [action_control_dependencies.py](file://app/api/action_control_dependencies.py)
- [0017_governed_action_control_plane.py](file://alembic/versions/0017_governed_action_control_plane.py)
- [0008_add_multi_approval_and_rollbacks.py](file://alembic/versions/0008_add_multi_approval_and_rollbacks.py)
- [0005_harden_agent_action_lifecycle.py](file://alembic/versions/0005_harden_agent_action_lifecycle.py)