# Multi-Organization Support

<cite>
**Referenced Files in This Document**
- [app/adapters/organization/__init__.py](file://app/adapters/organization/__init__.py)
- [app/adapters/organization/contract.py](file://app/adapters/organization/contract.py)
- [app/adapters/organization/mock_adapter.py](file://app/adapters/organization/mock_adapter.py)
- [app/repositories/nucleus_organization_repository.py](file://app/repositories/nucleus_organization_repository.py)
- [app/repositories/seat_repository.py](file://app/repositories/seat_repository.py)
- [app/repositories/user_repository.py](file://app/repositories/user_repository.py)
- [app/repositories/organization_overview_repository.py](file://app/repositories/organization_overview_repository.py)
- [app/services/nucleus_organization_service.py](file://app/services/nucleus_organization_service.py)
- [app/services/organization_service.py](file://app/services/organization_service.py)
- [app/schemas/nucleus_organization.py](file://app/schemas/nucleus_organization.py)
- [app/schemas/seat.py](file://app/schemas/seat.py)
- [app/schemas/user.py](file://app/schemas/user.py)
- [app/db/nucleus_models.py](file://app/db/nucleus_models.py)
- [app/db/orm_models.py](file://app/db/orm_models.py)
- [app/api/nucleus_routes.py](file://app/api/nucleus_routes.py)
- [app/core/security.py](file://app/core/security.py)
- [tests/test_nucleus_organization_api.py](file://tests/test_nucleus_organization_api.py)
- [tests/test_users_seats.py](file://tests/test_users_seats.py)
- [tests/test_organization_boundaries.py](file://tests/test_organization_boundaries.py)
- [tests/test_organization_overview.py](file://tests/test_organization_overview.py)
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

## Introduction
This document explains the multi-organization support subsystem, focusing on tenant isolation, seat management, and organization overview capabilities. It details how organizations are created and managed, how users are provisioned with seats, and how access boundaries are enforced to prevent cross-organization data leakage. The design uses an adapter pattern for external organization services and a contract-based approach to define service boundaries. Cross-organization query prevention, performance considerations for multi-tenant queries, and data synchronization strategies are also covered.

## Project Structure
The multi-organization subsystem spans adapters, repositories, services, schemas, database models, API routes, and tests:
- Adapters encapsulate external organization services behind contracts
- Repositories implement persistence and projection logic for organizations, seats, and users
- Services orchestrate business logic and enforce boundaries
- Schemas define request/response shapes
- Database models represent entities and relationships
- API routes expose administrative endpoints
- Tests validate behavior including boundaries and seat management

```mermaid
graph TB
subgraph "Adapters"
A1["organization/contract.py"]
A2["organization/mock_adapter.py"]
end
subgraph "Repositories"
R1["nucleus_organization_repository.py"]
R2["seat_repository.py"]
R3["user_repository.py"]
R4["organization_overview_repository.py"]
end
subgraph "Services"
S1["nucleus_organization_service.py"]
S2["organization_service.py"]
end
subgraph "Schemas"
SC1["nucleus_organization.py"]
SC2["seat.py"]
SC3["user.py"]
end
subgraph "DB Models"
M1["nucleus_models.py"]
M2["orm_models.py"]
end
subgraph "API"
AP1["nucleus_routes.py"]
end
subgraph "Security"
SEC1["security.py"]
end
AP1 --> S1
AP1 --> S2
S1 --> R1
S1 --> R2
S1 --> R3
S2 --> R4
S1 --> A1
A1 --> A2
R1 --> M1
R2 --> M1
R3 --> M1
R4 --> M1
S1 --> SC1
S1 --> SC2
S1 --> SC3
AP1 --> SEC1
```

**Diagram sources**
- [app/adapters/organization/contract.py](file://app/adapters/organization/contract.py)
- [app/adapters/organization/mock_adapter.py](file://app/adapters/organization/mock_adapter.py)
- [app/repositories/nucleus_organization_repository.py](file://app/repositories/nucleus_organization_repository.py)
- [app/repositories/seat_repository.py](file://app/repositories/seat_repository.py)
- [app/repositories/user_repository.py](file://app/repositories/user_repository.py)
- [app/repositories/organization_overview_repository.py](file://app/repositories/organization_overview_repository.py)
- [app/services/nucleus_organization_service.py](file://app/services/nucleus_organization_service.py)
- [app/services/organization_service.py](file://app/services/organization_service.py)
- [app/schemas/nucleus_organization.py](file://app/schemas/nucleus_organization.py)
- [app/schemas/seat.py](file://app/schemas/seat.py)
- [app/schemas/user.py](file://app/schemas/user.py)
- [app/db/nucleus_models.py](file://app/db/nucleus_models.py)
- [app/db/orm_models.py](file://app/db/orm_models.py)
- [app/api/nucleus_routes.py](file://app/api/nucleus_routes.py)
- [app/core/security.py](file://app/core/security.py)

**Section sources**
- [app/adapters/organization/contract.py](file://app/adapters/organization/contract.py)
- [app/adapters/organization/mock_adapter.py](file://app/adapters/organization/mock_adapter.py)
- [app/repositories/nucleus_organization_repository.py](file://app/repositories/nucleus_organization_repository.py)
- [app/repositories/seat_repository.py](file://app/repositories/seat_repository.py)
- [app/repositories/user_repository.py](file://app/repositories/user_repository.py)
- [app/repositories/organization_overview_repository.py](file://app/repositories/organization_overview_repository.py)
- [app/services/nucleus_organization_service.py](file://app/services/nucleus_organization_service.py)
- [app/services/organization_service.py](file://app/services/organization_service.py)
- [app/schemas/nucleus_organization.py](file://app/schemas/nucleus_organization.py)
- [app/schemas/seat.py](file://app/schemas/seat.py)
- [app/schemas/user.py](file://app/schemas/user.py)
- [app/db/nucleus_models.py](file://app/db/nucleus_models.py)
- [app/db/orm_models.py](file://app/db/orm_models.py)
- [app/api/nucleus_routes.py](file://app/api/nucleus_routes.py)
- [app/core/security.py](file://app/core/security.py)

## Core Components
- Adapter Contract and Implementation: Defines the interface for external organization services and provides a mock implementation for testing.
- Organization Repository: Persists and retrieves organization entities and projections.
- Seat Repository: Manages license allocation and user-seat assignments.
- User Repository: Handles user provisioning and membership within organizations.
- Organization Overview Repository: Provides aggregated views for administrative dashboards and cross-organization reporting.
- Services: Orchestrate operations such as creating organizations, assigning seats, and enforcing boundaries.
- Schemas: Define typed request/response structures for APIs.
- DB Models: Represent core entities and relationships.
- Security: Enforces authentication and authorization checks at API boundaries.

Key responsibilities:
- Tenant isolation: All reads/writes must be scoped to a specific organization context.
- Seat management: Track available licenses and enforce assignment limits.
- Access control: Ensure users can only access resources within their assigned organization.
- Cross-org prevention: Reject or sanitize queries that attempt to span multiple organizations.

**Section sources**
- [app/adapters/organization/contract.py](file://app/adapters/organization/contract.py)
- [app/adapters/organization/mock_adapter.py](file://app/adapters/organization/mock_adapter.py)
- [app/repositories/nucleus_organization_repository.py](file://app/repositories/nucleus_organization_repository.py)
- [app/repositories/seat_repository.py](file://app/repositories/seat_repository.py)
- [app/repositories/user_repository.py](file://app/repositories/user_repository.py)
- [app/repositories/organization_overview_repository.py](file://app/repositories/organization_overview_repository.py)
- [app/services/nucleus_organization_service.py](file://app/services/nucleus_organization_service.py)
- [app/services/organization_service.py](file://app/services/organization_service.py)
- [app/schemas/nucleus_organization.py](file://app/schemas/nucleus_organization.py)
- [app/schemas/seat.py](file://app/schemas/seat.py)
- [app/schemas/user.py](file://app/schemas/user.py)
- [app/db/nucleus_models.py](file://app/db/nucleus_models.py)
- [app/db/orm_models.py](file://app/db/orm_models.py)
- [app/core/security.py](file://app/core/security.py)

## Architecture Overview
The subsystem follows layered architecture with clear boundaries:
- API layer exposes endpoints for organization administration and seat management.
- Service layer enforces business rules, tenant scoping, and cross-org prevention.
- Repository layer persists data and builds projections for dashboards.
- Adapter layer abstracts external organization services via contracts.
- Security middleware validates requests and injects organization context.

```mermaid
sequenceDiagram
participant Client as "Client"
participant API as "Nucleus Routes"
participant Sec as "Security"
participant OrgSvc as "Nucleus Organization Service"
participant OrgRepo as "Organization Repository"
participant SeatRepo as "Seat Repository"
participant UserRepo as "User Repository"
participant Adapter as "Organization Adapter"
Client->>API : "POST /organizations"
API->>Sec : "Validate auth and org context"
Sec-->>API : "Context resolved"
API->>OrgSvc : "Create organization"
OrgSvc->>Adapter : "External org creation (if needed)"
Adapter-->>OrgSvc : "Result"
OrgSvc->>OrgRepo : "Persist organization"
OrgRepo-->>OrgSvc : "Created entity"
OrgSvc->>SeatRepo : "Initialize default seats"
SeatRepo-->>OrgSvc : "Seats allocated"
OrgSvc-->>API : "Organization created"
API-->>Client : "201 Created"
```

**Diagram sources**
- [app/api/nucleus_routes.py](file://app/api/nucleus_routes.py)
- [app/core/security.py](file://app/core/security.py)
- [app/services/nucleus_organization_service.py](file://app/services/nucleus_organization_service.py)
- [app/repositories/nucleus_organization_repository.py](file://app/repositories/nucleus_organization_repository.py)
- [app/repositories/seat_repository.py](file://app/repositories/seat_repository.py)
- [app/adapters/organization/contract.py](file://app/adapters/organization/contract.py)

## Detailed Component Analysis

### Adapter Pattern for External Organization Services
The adapter defines a contract for interacting with external organization services and includes a mock implementation for testing. This decouples internal logic from external dependencies and enables consistent behavior across environments.

```mermaid
classDiagram
class OrganizationAdapterContract {
+create_organization(data)
+update_organization(id, data)
+get_organization(id)
+list_organizations()
}
class MockOrganizationAdapter {
-store : dict
+create_organization(data)
+update_organization(id, data)
+get_organization(id)
+list_organizations()
}
OrganizationAdapterContract <|.. MockOrganizationAdapter : "implements"
```

**Diagram sources**
- [app/adapters/organization/contract.py](file://app/adapters/organization/contract.py)
- [app/adapters/organization/mock_adapter.py](file://app/adapters/organization/mock_adapter.py)

**Section sources**
- [app/adapters/organization/contract.py](file://app/adapters/organization/contract.py)
- [app/adapters/organization/mock_adapter.py](file://app/adapters/organization/mock_adapter.py)

### Organization Creation Flow
Creating an organization involves validating input, invoking external services if required, persisting the organization, and initializing seat allocations.

```mermaid
flowchart TD
Start(["Start"]) --> Validate["Validate request payload"]
Validate --> CallAdapter["Call adapter to create external org"]
CallAdapter --> Persist["Persist organization in repository"]
Persist --> InitSeats["Initialize default seats"]
InitSeats --> Return["Return created organization"]
Return --> End(["End"])
```

**Diagram sources**
- [app/services/nucleus_organization_service.py](file://app/services/nucleus_organization_service.py)
- [app/repositories/nucleus_organization_repository.py](file://app/repositories/nucleus_organization_repository.py)
- [app/repositories/seat_repository.py](file://app/repositories/seat_repository.py)
- [app/adapters/organization/contract.py](file://app/adapters/organization/contract.py)

**Section sources**
- [app/services/nucleus_organization_service.py](file://app/services/nucleus_organization_service.py)
- [app/repositories/nucleus_organization_repository.py](file://app/repositories/nucleus_organization_repository.py)
- [app/repositories/seat_repository.py](file://app/repositories/seat_repository.py)
- [app/adapters/organization/contract.py](file://app/adapters/organization/contract.py)

### Seat Management System
Seat management tracks license allocation and user provisioning. Seats are tied to organizations and users, ensuring access boundaries and preventing over-allocation.

```mermaid
classDiagram
class Seat {
+id
+organization_id
+user_id
+status
+assigned_at
}
class SeatRepository {
+allocate_seat(org_id, user_id)
+deallocate_seat(seat_id)
+list_seats(org_id)
+check_available(org_id)
}
class NucleusOrganizationService {
+assign_user_to_org(org_id, user_id)
+revoke_user_from_org(org_id, user_id)
}
SeatRepository --> Seat : "manages"
NucleusOrganizationService --> SeatRepository : "uses"
```

**Diagram sources**
- [app/repositories/seat_repository.py](file://app/repositories/seat_repository.py)
- [app/services/nucleus_organization_service.py](file://app/services/nucleus_organization_service.py)

**Section sources**
- [app/repositories/seat_repository.py](file://app/repositories/seat_repository.py)
- [app/services/nucleus_organization_service.py](file://app/services/nucleus_organization_service.py)

### Organization Overview Repository
The overview repository aggregates data for administrative dashboards and cross-organization reporting. It provides read-only projections optimized for analytics and summaries.

```mermaid
classDiagram
class OrganizationOverviewRepository {
+get_dashboard_metrics()
+get_cross_org_report(filters)
+get_usage_stats(period)
}
class OrganizationService {
+get_overview_data(filters)
}
OrganizationService --> OrganizationOverviewRepository : "queries"
```

**Diagram sources**
- [app/repositories/organization_overview_repository.py](file://app/repositories/organization_overview_repository.py)
- [app/services/organization_service.py](file://app/services/organization_service.py)

**Section sources**
- [app/repositories/organization_overview_repository.py](file://app/repositories/organization_overview_repository.py)
- [app/services/organization_service.py](file://app/services/organization_service.py)

### Data Models and Relationships
Organizations, seats, and users form the core data model. Relationships ensure referential integrity and enforce tenant scoping.

```mermaid
erDiagram
ORGANIZATION {
uuid id PK
string name
timestamp created_at
boolean active
}
SEAT {
uuid id PK
uuid organization_id FK
uuid user_id FK
enum status
timestamp assigned_at
}
USER {
uuid id PK
string email
string display_name
timestamp created_at
}
ORGANIZATION ||--o{ SEAT : "has many"
USER ||--o{ SEAT : "assigned to"
```

**Diagram sources**
- [app/db/nucleus_models.py](file://app/db/nucleus_models.py)
- [app/db/orm_models.py](file://app/db/orm_models.py)

**Section sources**
- [app/db/nucleus_models.py](file://app/db/nucleus_models.py)
- [app/db/orm_models.py](file://app/db/orm_models.py)

### API Endpoints for Multi-Organization Operations
Administrative endpoints allow creating organizations, managing seats, and retrieving overview data. Requests are authenticated and scoped to the current organization context.

```mermaid
sequenceDiagram
participant Admin as "Admin Client"
participant API as "Nucleus Routes"
participant Sec as "Security"
participant OrgSvc as "Organization Service"
participant Repo as "Repositories"
Admin->>API : "GET /overview?filters=..."
API->>Sec : "Verify admin role and org context"
Sec-->>API : "Authorized"
API->>OrgSvc : "Fetch overview data"
OrgSvc->>Repo : "Query overview repository"
Repo-->>OrgSvc : "Aggregated metrics"
OrgSvc-->>API : "Overview response"
API-->>Admin : "200 OK"
```

**Diagram sources**
- [app/api/nucleus_routes.py](file://app/api/nucleus_routes.py)
- [app/core/security.py](file://app/core/security.py)
- [app/services/organization_service.py](file://app/services/organization_service.py)
- [app/repositories/organization_overview_repository.py](file://app/repositories/organization_overview_repository.py)

**Section sources**
- [app/api/nucleus_routes.py](file://app/api/nucleus_routes.py)
- [app/core/security.py](file://app/core/security.py)
- [app/services/organization_service.py](file://app/services/organization_service.py)
- [app/repositories/organization_overview_repository.py](file://app/repositories/organization_overview_repository.py)

### Boundary Enforcement and Cross-Organization Query Prevention
Boundary enforcement ensures all queries include organization scoping. Cross-organization attempts are rejected early in the pipeline.

```mermaid
flowchart TD
Entry(["Request Entry"]) --> ResolveCtx["Resolve organization context"]
ResolveCtx --> HasCtx{"Context present?"}
HasCtx --> |No| Deny["Deny request - missing org context"]
HasCtx --> |Yes| ApplyScope["Apply org filter to all queries"]
ApplyScope --> CheckCross["Detect cross-org references"]
CheckCross --> |Found| Block["Block operation - cross-org violation"]
CheckCross --> |None| Proceed["Proceed with scoped operation"]
Deny --> Exit(["Exit"])
Block --> Exit
Proceed --> Exit
```

**Diagram sources**
- [app/core/security.py](file://app/core/security.py)
- [app/repositories/nucleus_organization_repository.py](file://app/repositories/nucleus_organization_repository.py)
- [app/repositories/seat_repository.py](file://app/repositories/seat_repository.py)
- [app/repositories/user_repository.py](file://app/repositories/user_repository.py)

**Section sources**
- [app/core/security.py](file://app/core/security.py)
- [app/repositories/nucleus_organization_repository.py](file://app/repositories/nucleus_organization_repository.py)
- [app/repositories/seat_repository.py](file://app/repositories/seat_repository.py)
- [app/repositories/user_repository.py](file://app/repositories/user_repository.py)

### Concrete Examples from Codebase
- Organization creation: See test cases demonstrating POST flows and validation.
- User assignment: See tests covering seat allocation and user provisioning.
- Boundary enforcement: See tests asserting cross-org query prevention.

**Section sources**
- [tests/test_nucleus_organization_api.py](file://tests/test_nucleus_organization_api.py)
- [tests/test_users_seats.py](file://tests/test_users_seats.py)
- [tests/test_organization_boundaries.py](file://tests/test_organization_boundaries.py)

## Dependency Analysis
The subsystem exhibits low coupling between layers and strong cohesion within components. Dependencies flow downward: API -> Services -> Repositories -> DB Models. Adapters are isolated behind contracts, minimizing external impact.

```mermaid
graph TB
API["nucleus_routes.py"] --> SVC1["nucleus_organization_service.py"]
API --> SVC2["organization_service.py"]
SVC1 --> REP1["nucleus_organization_repository.py"]
SVC1 --> REP2["seat_repository.py"]
SVC1 --> REP3["user_repository.py"]
SVC2 --> REP4["organization_overview_repository.py"]
REP1 --> DB1["nucleus_models.py"]
REP2 --> DB1
REP3 --> DB1
REP4 --> DB1
SVC1 --> ADP["organization/contract.py"]
ADP --> ADP2["organization/mock_adapter.py"]
API --> SEC["security.py"]
```

**Diagram sources**
- [app/api/nucleus_routes.py](file://app/api/nucleus_routes.py)
- [app/services/nucleus_organization_service.py](file://app/services/nucleus_organization_service.py)
- [app/services/organization_service.py](file://app/services/organization_service.py)
- [app/repositories/nucleus_organization_repository.py](file://app/repositories/nucleus_organization_repository.py)
- [app/repositories/seat_repository.py](file://app/repositories/seat_repository.py)
- [app/repositories/user_repository.py](file://app/repositories/user_repository.py)
- [app/repositories/organization_overview_repository.py](file://app/repositories/organization_overview_repository.py)
- [app/db/nucleus_models.py](file://app/db/nucleus_models.py)
- [app/adapters/organization/contract.py](file://app/adapters/organization/contract.py)
- [app/adapters/organization/mock_adapter.py](file://app/adapters/organization/mock_adapter.py)
- [app/core/security.py](file://app/core/security.py)

**Section sources**
- [app/api/nucleus_routes.py](file://app/api/nucleus_routes.py)
- [app/services/nucleus_organization_service.py](file://app/services/nucleus_organization_service.py)
- [app/services/organization_service.py](file://app/services/organization_service.py)
- [app/repositories/nucleus_organization_repository.py](file://app/repositories/nucleus_organization_repository.py)
- [app/repositories/seat_repository.py](file://app/repositories/seat_repository.py)
- [app/repositories/user_repository.py](file://app/repositories/user_repository.py)
- [app/repositories/organization_overview_repository.py](file://app/repositories/organization_overview_repository.py)
- [app/db/nucleus_models.py](file://app/db/nucleus_models.py)
- [app/adapters/organization/contract.py](file://app/adapters/organization/contract.py)
- [app/adapters/organization/mock_adapter.py](file://app/adapters/organization/mock_adapter.py)
- [app/core/security.py](file://app/core/security.py)

## Performance Considerations
- Indexing: Ensure indexes on organization-scoped foreign keys (e.g., organization_id, user_id) to optimize lookups and joins.
- Projection Queries: Use dedicated overview queries to avoid heavy aggregations on transactional tables.
- Caching: Cache frequently accessed organization metadata and seat availability where appropriate.
- Pagination: Implement pagination for list endpoints to reduce payload sizes.
- Batch Operations: Prefer batch inserts/updates for seat provisioning to minimize round trips.

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
Common issues and resolutions:
- Missing organization context: Verify security middleware resolves org context before processing requests.
- Cross-org violations: Inspect logs for boundary enforcement rejections; ensure filters are applied consistently.
- Seat allocation failures: Check seat availability and constraints; review repository error handling.
- Overview data inconsistencies: Validate projection updates and synchronization jobs.

**Section sources**
- [app/core/security.py](file://app/core/security.py)
- [app/repositories/seat_repository.py](file://app/repositories/seat_repository.py)
- [app/repositories/organization_overview_repository.py](file://app/repositories/organization_overview_repository.py)

## Conclusion
The multi-organization support subsystem provides robust tenant isolation, seat management, and administrative reporting through a layered architecture with clear boundaries. The adapter pattern and contract-based approach enable flexible integration with external services while maintaining consistency. Cross-organization query prevention and performance optimizations ensure secure and efficient operations across organizations.

[No sources needed since this section summarizes without analyzing specific files]