# Data Architecture & Storage

<cite>
**Referenced Files in This Document**
- [base.py](file://app/db/base.py)
- [session.py](file://app/db/session.py)
- [orm_models.py](file://app/db/orm_models.py)
- [action_models.py](file://app/db/action_models.py)
- [agent_run_models.py](file://app/db/agent_run_models.py)
- [nucleus_models.py](file://app/db/nucleus_models.py)
- [audit_repository.py](file://app/repositories/audit_repository.py)
- [organization_repository.py](file://app/repositories/organization_repository.py)
- [conversation_repository.py](file://app/repositories/conversation_repository.py)
- [env.py](file://alembic/env.py)
- [0001_initial.py](file://alembic/versions/0001_initial.py)
- [config.py](file://app/core/config.py)
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

This document provides comprehensive architectural documentation for the data layer design and storage strategies implemented in the application. The system employs a modern, scalable architecture built around SQLAlchemy ORM, repository pattern implementation, multi-tenant data isolation, audit trail systems, and robust data migration management through Alembic.

The data layer is designed to support complex business requirements including agent orchestration, organizational boundaries, conversation management, and comprehensive audit logging while maintaining high performance and data integrity.

## Project Structure

The data layer follows a clean separation of concerns with distinct responsibilities:

```mermaid
graph TB
subgraph "Data Layer Architecture"
A[API Layer] --> B[Repository Layer]
B --> C[ORM Models]
C --> D[Database Session]
D --> E[(PostgreSQL)]
F[Alembic Migrations] --> C
G[Audit System] --> B
H[Multi-tenant Isolation] --> B
subgraph "Repository Pattern"
B1[Organization Repository]
B2[Agent Action Repository]
B3[Conversation Repository]
B4[Audit Repository]
end
subgraph "ORM Models"
C1[Base Model]
C2[Domain Models]
C3[Relationships]
end
end
```

**Diagram sources**
- [base.py](file://app/db/base.py)
- [session.py](file://app/db/session.py)
- [orm_models.py](file://app/db/orm_models.py)

**Section sources**
- [base.py](file://app/db/base.py)
- [session.py](file://app/db/session.py)
- [orm_models.py](file://app/db/orm_models.py)

## Core Components

### Database Session Management

The session management provides connection pooling, transaction handling, and tenant-aware database access. It implements proper resource cleanup and error handling patterns.

### Repository Pattern Implementation

The repository layer abstracts database operations behind clean interfaces, providing:
- Consistent CRUD operations
- Complex query composition
- Transaction boundary management
- Multi-tenant data isolation enforcement
- Audit trail integration

### ORM Model Architecture

SQLAlchemy models implement:
- Declarative base classes
- Relationship definitions
- Validation constraints
- Multi-tenant scoping
- Audit field automation

**Section sources**
- [session.py](file://app/db/session.py)
- [audit_repository.py](file://app/repositories/audit_repository.py)
- [organization_repository.py](file://app/repositories/organization_repository.py)

## Architecture Overview

The data architecture follows a layered approach with clear separation between presentation, business logic, and data persistence:

```mermaid
sequenceDiagram
participant Client as "Client Application"
participant API as "API Layer"
participant Repo as "Repository Layer"
participant ORM as "ORM Models"
participant DB as "Database"
Client->>API : HTTP Request
API->>Repo : Business Operation
Repo->>ORM : Query/Update
ORM->>DB : SQL Execution
DB-->>ORM : Results
ORM-->>Repo : Domain Objects
Repo-->>API : Response Data
API-->>Client : JSON Response
Note over Repo,DB : Multi-tenant isolation enforced
Note over Repo,API : Audit logging integrated
```

**Diagram sources**
- [session.py](file://app/db/session.py)
- [audit_repository.py](file://app/repositories/audit_repository.py)

## Detailed Component Analysis

### Repository Pattern Implementation

The repository pattern provides clean abstraction over database operations, ensuring loose coupling between business logic and data access:

```mermaid
classDiagram
class BaseRepository {
+session Session
+find_by_id(id) Optional[T]
+create(data) T
+update(entity) T
+delete(entity) bool
+query_builder() QueryBuilder
}
class OrganizationRepository {
+get_by_domain(domain) Organization
+get_active_organizations() List[Organization]
+validate_tenant_access(org_id) bool
}
class AgentActionRepository {
+find_pending_actions() List[AgentAction]
+update_action_state(action_id, state) AgentAction
+get_action_history(action_id) List[ActionEvent]
}
class AuditRepository {
+log_audit_event(event_data) AuditEvent
+get_audit_trail(entity_type, entity_id) List[AuditEvent]
+compliance_report(start_date, end_date) Report
}
BaseRepository <|-- OrganizationRepository
BaseRepository <|-- AgentActionRepository
BaseRepository <|-- AuditRepository
```

**Diagram sources**
- [audit_repository.py](file://app/repositories/audit_repository.py)
- [organization_repository.py](file://app/repositories/organization_repository.py)

#### Key Repository Features:

1. **Transaction Management**: Automatic commit/rollback handling
2. **Query Composition**: Fluent API for complex queries
3. **Error Handling**: Consistent exception patterns
4. **Caching Integration**: Redis-backed query result caching
5. **Audit Trail**: Automatic event logging for all mutations

**Section sources**
- [audit_repository.py](file://app/repositories/audit_repository.py)
- [organization_repository.py](file://app/repositories/organization_repository.py)

### ORM Model Architecture

The SQLAlchemy model architecture implements comprehensive relationships, constraints, and validation:

```mermaid
erDiagram
ORGANIZATION {
uuid id PK
string name
string domain UK
boolean is_active
timestamp created_at
timestamp updated_at
}
USER {
uuid id PK
string email UK
uuid organization_id FK
string role
boolean is_active
timestamp created_at
}
AGENT_ACTION {
uuid id PK
uuid organization_id FK
string action_type
enum status
jsonb payload
uuid proposed_by FK
timestamp created_at
timestamp updated_at
}
CONVERSATION {
uuid id PK
uuid organization_id FK
string title
jsonb messages
enum status
timestamp created_at
timestamp updated_at
}
AUDIT_EVENT {
uuid id PK
string entity_type
uuid entity_id
string action
jsonb changes
uuid actor_id
timestamp occurred_at
}
ORGANIZATION ||--o{ USER : has_many
ORGANIZATION ||--o{ AGENT_ACTION : owns
ORGANIZATION ||--o{ CONVERSATION : contains
USER ||--o{ AUDIT_EVENT : creates
AGENT_ACTION ||--o{ AUDIT_EVENT : generates
```

**Diagram sources**
- [orm_models.py](file://app/db/orm_models.py)
- [action_models.py](file://app/db/action_models.py)
- [agent_run_models.py](file://app/db/agent_run_models.py)

#### Model Relationships and Constraints:

1. **Foreign Key Constraints**: Referential integrity enforcement
2. **Unique Constraints**: Email uniqueness, domain uniqueness
3. **Check Constraints**: Status validation, data format validation
4. **Cascade Operations**: Proper deletion and update propagation
5. **Indexing Strategy**: Optimized query performance

**Section sources**
- [orm_models.py](file://app/db/orm_models.py)
- [action_models.py](file://app/db/action_models.py)

### Multi-Tenant Data Isolation

The system implements strict organization boundary enforcement through multiple layers:

```mermaid
flowchart TD
A[Request Received] --> B[Extract Tenant Context]
B --> C{Tenant Valid?}
C --> |No| D[Return 403 Forbidden]
C --> |Yes| E[Apply Tenant Filter]
E --> F[Execute Database Query]
F --> G[Validate Results Belong to Tenant]
G --> |Invalid| H[Security Violation - Log & Block]
G --> |Valid| I[Return Results]
J[Repository Layer] --> K[Automatic Tenant Scoping]
L[Model Level] --> M[Organization ID Required]
N[Database Level] --> O[Row-Level Security Policies]
```

**Diagram sources**
- [organization_repository.py](file://app/repositories/organization_repository.py)

#### Isolation Strategies:

1. **Application Level**: Automatic organization_id filtering
2. **Repository Level**: Tenant-scoped query builders
3. **Database Level**: Row-level security policies (optional)
4. **Validation Level**: Cross-tenant access prevention

**Section sources**
- [organization_repository.py](file://app/repositories/organization_repository.py)

### Audit Trail System

The audit system provides immutable logging with compliance requirements:

```mermaid
sequenceDiagram
participant App as "Application"
participant Repo as "Repository"
participant Audit as "Audit Service"
participant DB as "Audit Database"
App->>Repo : Update Entity
Repo->>Repo : Capture Before State
Repo->>Repo : Apply Changes
Repo->>Repo : Capture After State
Repo->>Audit : Create Audit Event
Audit->>Audit : Validate Compliance Rules
Audit->>DB : Store Immutable Record
DB-->>Audit : Confirmation
Audit-->>Repo : Success
Repo-->>App : Updated Entity
```

**Diagram sources**
- [audit_repository.py](file://app/repositories/audit_repository.py)

#### Audit Features:

1. **Immutable Logging**: Append-only audit records
2. **Change Tracking**: Before/after state snapshots
3. **Compliance Reporting**: Regulatory requirement support
4. **Access Control**: Restricted audit log access
5. **Retention Policies**: Configurable data retention

**Section sources**
- [audit_repository.py](file://app/repositories/audit_repository.py)

### Database Schema Evolution with Alembic

The migration system manages schema evolution through versioned migrations:

```mermaid
flowchart LR
A[Code Change] --> B[Generate Migration]
B --> C[Review Migration]
C --> D[Test Migration]
D --> E[Deploy Migration]
E --> F[Production Rollout]
G[Migration File] --> H[Up Function]
G --> I[Down Function]
H --> J[Schema Upgrade]
I --> K[Schema Downgrade]
L[Version Tracking] --> M[Current Version]
L --> N[Migration History]
```

**Diagram sources**
- [env.py](file://alembic/env.py)
- [0001_initial.py](file://alembic/versions/0001_initial.py)

#### Migration Best Practices:

1. **Idempotent Migrations**: Safe re-execution capability
2. **Data Preservation**: Backward-compatible schema changes
3. **Testing Strategy**: Migration testing in CI/CD pipeline
4. **Rollback Support**: Safe downgrade procedures
5. **Documentation**: Clear change descriptions

**Section sources**
- [env.py](file://alembic/env.py)
- [0001_initial.py](file://alembic/versions/0001_initial.py)

## Dependency Analysis

The data layer dependencies follow clean architecture principles:

```mermaid
graph TD
subgraph "External Dependencies"
A[SQLAlchemy] --> B[Database Driver]
C[Alembic] --> A
D[Redis Client] --> E[Caching Layer]
end
subgraph "Internal Dependencies"
F[Repositories] --> G[ORM Models]
G --> H[Base Classes]
I[Audit System] --> F
J[Multi-tenant] --> F
end
subgraph "Configuration"
K[Config Module] --> L[Database URLs]
K --> M[Cache Settings]
K --> N[Audit Configuration]
end
F --> A
F --> D
G --> A
```

**Diagram sources**
- [config.py](file://app/core/config.py)
- [session.py](file://app/db/session.py)

### Key Dependencies:

1. **SQLAlchemy**: ORM framework for database abstraction
2. **Alembic**: Database migration management
3. **Redis**: Caching layer for performance optimization
4. **Pydantic**: Data validation and serialization
5. **UUID**: Unique identifier generation

**Section sources**
- [config.py](file://app/core/config.py)
- [session.py](file://app/db/session.py)

## Performance Considerations

### Query Optimization Strategies

1. **Indexing Strategy**: Strategic index creation for frequently queried columns
2. **Connection Pooling**: Efficient database connection management
3. **Query Caching**: Redis-backed result caching for expensive queries
4. **Lazy Loading**: Optimal relationship loading strategies
5. **Batch Operations**: Bulk insert/update operations for better throughput

### Caching Strategy with Redis

The caching layer implements multiple cache levels:

```mermaid
flowchart TD
A[Cache Request] --> B{Cache Hit?}
B --> |Yes| C[Return Cached Data]
B --> |No| D[Query Database]
D --> E[Process Results]
E --> F[Store in Cache]
F --> G[Return Data]
H[Cache Invalidation] --> I[Entity Update]
H --> J[Delete Related Keys]
H --> K[Update Expiration]
```

#### Cache Levels:

1. **Query Result Cache**: Expensive query results
2. **Entity Cache**: Frequently accessed entities
3. **Computed Value Cache**: Aggregated data and statistics
4. **Session Cache**: User session data

**Section sources**
- [session.py](file://app/db/session.py)

## Troubleshooting Guide

### Common Database Issues

1. **Connection Pool Exhaustion**: Monitor pool usage and adjust settings
2. **Slow Queries**: Use query profiling and add appropriate indexes
3. **Deadlocks**: Analyze transaction patterns and optimize locking
4. **Memory Leaks**: Monitor connection lifecycle and cleanup
5. **Migration Failures**: Review migration history and rollback procedures

### Performance Monitoring

1. **Query Performance**: Slow query logging and analysis
2. **Connection Metrics**: Pool utilization and wait times
3. **Cache Hit Rates**: Cache effectiveness monitoring
4. **Audit Log Volume**: Storage growth and performance impact

### Debugging Tools

1. **SQL Logging**: Enable detailed query logging in development
2. **Audit Trail Analysis**: Investigate data changes and access patterns
3. **Migration Testing**: Comprehensive test coverage for schema changes
4. **Load Testing**: Performance validation under various workloads

## Conclusion

The data architecture provides a robust, scalable foundation supporting complex business requirements through well-defined patterns and best practices. The repository pattern ensures clean separation of concerns, while multi-tenant isolation guarantees data security and compliance. The comprehensive audit trail system meets regulatory requirements, and the migration strategy enables safe schema evolution.

Key strengths include:
- Clean abstraction through repository pattern
- Strong multi-tenant data isolation
- Comprehensive audit and compliance features
- Scalable caching strategy
- Robust migration management
- Performance optimization techniques

This architecture supports the application's growth while maintaining data integrity, security, and performance standards.