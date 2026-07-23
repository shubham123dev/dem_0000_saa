# Feature Modules

<cite>
**Referenced Files in This Document**
- [agent-conversation.store.ts](file://frontend/src/app/features/assistant-conversation/agent-conversation.store.ts)
- [approval-center.store.ts](file://frontend/src/app/features/approval-center/approval-center.store.ts)
- [conversation-list.store.ts](file://frontend/src/app/features/conversation-list/conversation-list.store.ts)
- [proposal-control.facade.ts](file://frontend/src/app/core/action-control/proposal-control.facade.ts)
- [agent-run-stream.service.ts](file://frontend/src/app/core/agent-run/agent-run-stream.service.ts)
- [assistant-activity.component.ts](file://frontend/src/app/features/assistant-conversation/assistant-activity/assistant-activity.component.ts)
- [assistant-composer.component.ts](file://frontend/src/app/features/assistant-conversation/assistant-composer/assistant-composer.component.ts)
- [assistant-message.component.ts](file://frontend/src/app/features/assistant-conversation/assistant-message/assistant-message.component.ts)
- [assistant-proposal-card.component.ts](file://frontend/src/app/features/assistant-conversation/assistant-proposal-card/assistant-proposal-card.component.ts)
- [approval-center.component.ts](file://frontend/src/app/features/approval-center/approval-center.component.ts)
- [conversation-list.component.ts](file://frontend/src/app/features/conversation-list/conversation-list.component.ts)
- [organization-workspace.component.ts](file://frontend/src/app/layout/workspace/organization-workspace.component.ts)
- [chat-view.component.ts](file://frontend/src/app/layout/workspace/chat-view.component.ts)
- [action-control-api.service.ts](file://frontend/src/app/core/action-control/action-control-api.service.ts)
- [conversation-api.service.ts](file://frontend/src/app/core/conversation/conversation-api.service.ts)
- [workplace-agent-api.service.ts](file://frontend/src/app/core/api/workplace-agent-api.service.ts)
- [current-user.store.ts](file://frontend/src/app/core/auth/current-user.store.ts)
- [app.config.ts](file://frontend/src/app/app.config.ts)
- [app.routes.ts](file://frontend/src/app/app.routes.ts)
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

This document provides comprehensive documentation for the feature-based module architecture of the Workplace Agent application. The system implements a modern Angular frontend with a clear separation of concerns across multiple feature modules, including assistant conversations, approval workflows, workspace management, and real-time communication capabilities.

The architecture follows established patterns for state management using stores, reactive data flows through services, and component hierarchies that promote reusability and maintainability. Each feature module encapsulates its own business logic, UI components, and state management, enabling independent development and testing.

## Project Structure

The application follows a feature-based architecture where each major functionality is organized into its own module with clear boundaries:

```mermaid
graph TB
subgraph "Feature Modules"
AC["Assistant Conversation<br/>Real-time chat interface"]
AP["Approval Center<br/>Action review workflows"]
CL["Conversation List<br/>Navigation hub"]
WS["Workspace Management<br/>Organization navigation"]
end
subgraph "Core Services"
API["API Services<br/>HTTP clients"]
SSE["SSE Streams<br/>Real-time updates"]
STORE["State Stores<br/>Reactive data"]
AUTH["Auth Service<br/>User management"]
end
subgraph "Shared Components"
UI["UI Components<br/>Design system"]
LAYOUT["Layout Components<br/>Shell & navigation"]
end
AC --> API
AC --> SSE
AC --> STORE
AP --> API
AP --> STORE
CL --> API
CL --> STORE
WS --> API
WS --> STORE
API --> AUTH
SSE --> AUTH
STORE --> AUTH
```

**Diagram sources**
- [app.config.ts](file://frontend/src/app/app.config.ts)
- [app.routes.ts](file://frontend/src/app/app.routes.ts)

**Section sources**
- [app.config.ts](file://frontend/src/app/app.config.ts)
- [app.routes.ts](file://frontend/src/app/app.routes.ts)

## Core Components

### State Management Architecture

The application implements a store-based state management pattern where each feature maintains its own reactive state:

```mermaid
classDiagram
class Store {
+state Observable
+actions Function[]
+selectors Function[]
+dispatch(action) void
+select(selector) Observable
}
class AssistantConversationStore {
+messages Message[]
+activity Activity[]
+selectedProposal Proposal
+sendMessage(text) void
+updateActivity(activity) void
+handleProposal(proposal) void
}
class ApprovalCenterStore {
+pendingActions Action[]
+approvedActions Action[]
+reviewAction(action) void
+batchApprove(actions) void
+batchReject(actions) void
}
class ConversationListStore {
+conversations Conversation[]
+selectedConversation Conversation
+loadConversations() void
+selectConversation(id) void
}
Store <|-- AssistantConversationStore
Store <|-- ApprovalCenterStore
Store <|-- ConversationListStore
```

**Diagram sources**
- [agent-conversation.store.ts](file://frontend/src/app/features/assistant-conversation/agent-conversation.store.ts)
- [approval-center.store.ts](file://frontend/src/app/features/approval-center/approval-center.store.ts)
- [conversation-list.store.ts](file://frontend/src/app/features/conversation-list/conversation-list.store.ts)

### Real-time Communication Layer

The system uses Server-Sent Events (SSE) for real-time updates across all features:

```mermaid
sequenceDiagram
participant Client as "Frontend Client"
participant SSE as "SSE Stream Service"
participant API as "Backend API"
participant Store as "Feature Store"
Client->>SSE : Initialize connection
SSE->>API : Connect to /api/stream
API-->>SSE : Event stream
SSE->>Store : Dispatch event
Store->>Store : Update state
Store-->>Client : Reactive update
Note over Client,Store : Real-time bidirectional updates
```

**Diagram sources**
- [agent-run-stream.service.ts](file://frontend/src/app/core/agent-run/agent-run-stream.service.ts)
- [authenticated-sse-client.service.ts](file://frontend/src/app/core/sse/authenticated-sse-client.service.ts)

**Section sources**
- [agent-conversation.store.ts](file://frontend/src/app/features/assistant-conversation/agent-conversation.store.ts)
- [approval-center.store.ts](file://frontend/src/app/features/approval-center/approval-center.store.ts)
- [conversation-list.store.ts](file://frontend/src/app/features/conversation-list/conversation-list.store.ts)
- [agent-run-stream.service.ts](file://frontend/src/app/core/agent-run/agent-run-stream.service.ts)

## Architecture Overview

The application implements a layered architecture with clear separation between presentation, business logic, and data access layers:

```mermaid
graph TD
subgraph "Presentation Layer"
Components[Components]
Templates[Templates]
Styles[Styles]
end
subgraph "Business Logic Layer"
Stores[Stores]
Facades[Facades]
Services[Services]
end
subgraph "Data Access Layer"
APIServices[API Services]
SSEStreams[SSE Streams]
LocalStorage[Local Storage]
end
subgraph "External Systems"
BackendAPI[Backend API]
AuthProvider[Authentication Provider]
Database[(Database)]
end
Components --> Stores
Components --> Facades
Facades --> Services
Services --> APIServices
Services --> SSEStreams
APIServices --> BackendAPI
SSEStreams --> BackendAPI
Stores --> LocalStorage
```

**Diagram sources**
- [app.config.ts](file://frontend/src/app/app.config.ts)
- [workplace-agent-api.service.ts](file://frontend/src/app/core/api/workplace-agent-api.service.ts)

## Detailed Component Analysis

### Assistant Conversation Feature

The assistant conversation feature provides a real-time chat interface with message handling, activity streams, and proposal cards:

#### Component Hierarchy

```mermaid
graph TD
subgraph "Assistant Conversation Module"
MainComponent[Assistant Conversation Component]
subgraph "Message Handling"
Composer[Assistant Composer]
MessageDisplay[Assistant Message]
ActivityStream[Assistant Activity]
end
subgraph "Proposal Management"
ProposalCard[Assistant Proposal Card]
ProposalControl[Proposal Control Facade]
end
subgraph "State Management"
ConversationStore[Agent Conversation Store]
ResponseMapper[Response Mapper]
end
MainComponent --> Composer
MainComponent --> MessageDisplay
MainComponent --> ActivityStream
MainComponent --> ProposalCard
Composer --> ConversationStore
MessageDisplay --> ConversationStore
ActivityStream --> ConversationStore
ProposalCard --> ProposalControl
ProposalControl --> ConversationStore
ConversationStore --> ResponseMapper
end
```

**Diagram sources**
- [assistant-activity.component.ts](file://frontend/src/app/features/assistant-conversation/assistant-activity/assistant-activity.component.ts)
- [assistant-composer.component.ts](file://frontend/src/app/features/assistant-conversation/assistant-composer/assistant-composer.component.ts)
- [assistant-message.component.ts](file://frontend/src/app/features/assistant-conversation/assistant-message/assistant-message.component.ts)
- [assistant-proposal-card.component.ts](file://frontend/src/app/features/assistant-conversation/assistant-proposal-card/assistant-proposal-card.component.ts)
- [agent-conversation.store.ts](file://frontend/src/app/features/assistant-conversation/agent-conversation.store.ts)
- [proposal-control.facade.ts](file://frontend/src/app/core/action-control/proposal-control.facade.ts)

#### Real-time Message Flow

```mermaid
sequenceDiagram
participant User as "User"
participant Composer as "Assistant Composer"
participant Store as "Conversation Store"
participant API as "Conversation API"
participant SSE as "SSE Stream"
participant Display as "Message Display"
User->>Composer : Type message
User->>Composer : Send message
Composer->>Store : sendMessage(text)
Store->>API : POST /api/conversation/message
API-->>Store : Message created
Store->>Display : Add message to view
SSE->>Store : Real-time updates
Store->>Display : Update activity stream
Store->>Display : Show proposal cards
Note over User,Display : Real-time conversation experience
```

**Diagram sources**
- [assistant-composer.component.ts](file://frontend/src/app/features/assistant-conversation/assistant-composer/assistant-composer.component.ts)
- [conversation-api.service.ts](file://frontend/src/app/core/conversation/conversation-api.service.ts)
- [agent-run-stream.service.ts](file://frontend/src/app/core/agent-run/agent-run-stream.service.ts)

**Section sources**
- [assistant-activity.component.ts](file://frontend/src/app/features/assistant-conversation/assistant-activity/assistant-activity.component.ts)
- [assistant-composer.component.ts](file://frontend/src/app/features/assistant-conversation/assistant-composer/assistant-composer.component.ts)
- [assistant-message.component.ts](file://frontend/src/app/features/assistant-conversation/assistant-message/assistant-message.component.ts)
- [assistant-proposal-card.component.ts](file://frontend/src/app/features/assistant-conversation/assistant-proposal-card/assistant-proposal-card.component.ts)
- [agent-conversation.store.ts](file://frontend/src/app/features/assistant-conversation/agent-conversation.store.ts)
- [proposal-control.facade.ts](file://frontend/src/app/core/action-control/proposal-control.facade.ts)
- [conversation-api.service.ts](file://frontend/src/app/core/conversation/conversation-api.service.ts)

### Approval Center Feature

The approval center provides action review workflows with batch operations for managing agent actions:

#### Workflow Management

```mermaid
flowchart TD
Start([Pending Actions]) --> Review["Review Action Details"]
Review --> Decision{"Decision?"}
Decision --> |Approve| Approve["Approve Action"]
Decision --> |Reject| Reject["Reject Action"]
Decision --> |Batch| BatchOps["Batch Operations"]
Approve --> Execute["Execute Action"]
Reject --> Log["Log Rejection"]
BatchOps --> BatchApprove["Batch Approve"]
BatchOps --> BatchReject["Batch Reject"]
Execute --> Complete([Action Complete])
Log --> Complete
BatchApprove --> Complete
BatchReject --> Complete
Complete --> NextAction["Next Pending Action"]
NextAction --> Review
```

**Diagram sources**
- [approval-center.component.ts](file://frontend/src/app/features/approval-center/approval-center.component.ts)
- [approval-center.store.ts](file://frontend/src/app/features/approval-center/approval-center.store.ts)
- [action-control-api.service.ts](file://frontend/src/app/core/action-control/action-control-api.service.ts)

#### Batch Operations Pattern

```mermaid
sequenceDiagram
participant User as "User"
participant UI as "Approval Center UI"
participant Store as "Approval Store"
participant API as "Action Control API"
participant Stream as "SSE Stream"
User->>UI : Select multiple actions
User->>UI : Click batch approve
UI->>Store : batchApprove(actions[])
Store->>API : POST /api/actions/batch-approve
API-->>Store : Batch operation result
Store->>Stream : Emit batch completion event
Stream-->>UI : Update pending list
UI-->>User : Show success feedback
Note over User,UI : Efficient bulk action processing
```

**Diagram sources**
- [approval-center.store.ts](file://frontend/src/app/features/approval-center/approval-center.store.ts)
- [action-control-api.service.ts](file://frontend/src/app/core/action-control/action-control-api.service.ts)

**Section sources**
- [approval-center.component.ts](file://frontend/src/app/features/approval-center/approval-center.component.ts)
- [approval-center.store.ts](file://frontend/src/app/features/approval-center/approval-center.store.ts)
- [action-control-api.service.ts](file://frontend/src/app/core/action-control/action-control-api.service.ts)

### Workspace Management Feature

The workspace management provides organization navigation and resource browsing capabilities:

#### Organization Navigation

```mermaid
graph TD
subgraph "Workspace Layout"
Shell[App Shell]
Sidebar[Primary Sidebar]
ContentArea[Content Area]
end
subgraph "Organization Management"
OrgSelector[Organization Selector]
ResourceBrowser[Resource Browser]
WorkspaceView[Workspace View]
end
subgraph "Navigation State"
RouteService[Route Service]
OrgContext[Organization Context]
end
Shell --> Sidebar
Shell --> ContentArea
Sidebar --> OrgSelector
ContentArea --> WorkspaceView
OrgSelector --> RouteService
OrgSelector --> OrgContext
ResourceBrowser --> WorkspaceView
RouteService --> WorkspaceView
```

**Diagram sources**
- [organization-workspace.component.ts](file://frontend/src/app/layout/workspace/organization-workspace.component.ts)
- [chat-view.component.ts](file://frontend/src/app/layout/workspace/chat-view.component.ts)
- [primary-sidebar.component.ts](file://frontend/src/app/layout/primary-sidebar/primary-sidebar.component.ts)

#### Resource Browsing Interface

```mermaid
sequenceDiagram
participant User as "User"
participant Browser as "Resource Browser"
participant API as "Workplace API"
participant Store as "Workspace Store"
participant View as "Workspace View"
User->>Browser : Navigate to resource
Browser->>API : GET /api/resources/{id}
API-->>Browser : Resource details
Browser->>Store : Update resource state
Store->>View : Render resource view
View-->>User : Display resource
Note over User,View : Dynamic resource loading and display
```

**Diagram sources**
- [organization-workspace.component.ts](file://frontend/src/app/layout/workspace/organization-workspace.component.ts)
- [workplace-agent-api.service.ts](file://frontend/src/app/core/api/workplace-agent-api.service.ts)

**Section sources**
- [organization-workspace.component.ts](file://frontend/src/app/layout/workspace/organization-workspace.component.ts)
- [chat-view.component.ts](file://frontend/src/app/layout/workspace/chat-view.component.ts)
- [workplace-agent-api.service.ts](file://frontend/src/app/core/api/workplace-agent-api.service.ts)

## Dependency Analysis

The application follows clean dependency patterns with clear separation between features and shared services:

```mermaid
graph TD
subgraph "Feature Dependencies"
AC["Assistant Conversation"]
AP["Approval Center"]
CL["Conversation List"]
WS["Workspace Management"]
end
subgraph "Shared Dependencies"
API["API Services"]
STORE["State Stores"]
AUTH["Auth Service"]
ROUTING["Routing Service"]
end
subgraph "External Dependencies"
BACKEND["Backend API"]
SSE["SSE Streams"]
STORAGE["Local Storage"]
end
AC --> API
AC --> STORE
AC --> AUTH
AP --> API
AP --> STORE
CL --> API
CL --> STORE
WS --> API
WS --> STORE
API --> BACKEND
API --> SSE
STORE --> STORAGE
AUTH --> BACKEND
```

**Diagram sources**
- [app.config.ts](file://frontend/src/app/app.config.ts)
- [current-user.store.ts](file://frontend/src/app/core/auth/current-user.store.ts)

### Inter-Feature Communication

Features communicate through shared services and events rather than direct dependencies:

```mermaid
sequenceDiagram
participant FeatureA as "Feature A"
participant EventBus as "Event Bus"
participant FeatureB as "Feature B"
participant SharedStore as "Shared Store"
FeatureA->>EventBus : Emit event
EventBus->>FeatureB : Subscribe to event
FeatureA->>SharedStore : Update shared state
SharedStore->>FeatureB : Reactive update
Note over FeatureA,FeatureB : Loose coupling through events and shared state
```

**Section sources**
- [app.config.ts](file://frontend/src/app/app.config.ts)
- [current-user.store.ts](file://frontend/src/app/core/auth/current-user.store.ts)

## Performance Considerations

### State Management Optimization

The store-based architecture implements several performance optimizations:

- **Selective Updates**: Components subscribe only to specific state slices they need
- **Change Detection Batching**: Multiple state updates are batched to minimize re-renders
- **Lazy Loading**: Feature modules are loaded on-demand to reduce initial bundle size
- **Caching Strategy**: API responses are cached locally to reduce network requests

### Real-time Communication Efficiency

The SSE implementation includes:

- **Connection Pooling**: Multiple streams share a single connection when possible
- **Event Filtering**: Clients receive only relevant events based on their current context
- **Backpressure Handling**: Slow consumers don't block fast producers
- **Automatic Reconnection**: Failed connections are automatically retried with exponential backoff

## Troubleshooting Guide

### Common Issues and Solutions

#### Connection Problems
- **Symptom**: Real-time updates not working
- **Solution**: Check authentication token validity and SSE connection status
- **Debug**: Monitor network tab for SSE connection errors

#### State Synchronization Issues
- **Symptom**: UI shows stale data
- **Solution**: Verify store subscriptions and check for race conditions
- **Debug**: Enable debug logging in stores to track state changes

#### Performance Degradation
- **Symptom**: Application becomes slow with large datasets
- **Solution**: Implement virtual scrolling and pagination for large lists
- **Debug**: Use browser performance profiling to identify bottlenecks

**Section sources**
- [agent-run-stream.service.ts](file://frontend/src/app/core/agent-run/agent-run-stream.service.ts)
- [agent-conversation.store.ts](file://frontend/src/app/features/assistant-conversation/agent-conversation.store.ts)
- [approval-center.store.ts](file://frontend/src/app/features/approval-center/approval-center.store.ts)

## Conclusion

The feature-based module architecture provides a scalable and maintainable foundation for the Workplace Agent application. The clear separation of concerns, robust state management, and efficient real-time communication patterns enable rapid development while ensuring high performance and excellent user experience.

Key architectural strengths include:

- **Modular Design**: Each feature operates independently with well-defined interfaces
- **Reactive State Management**: Stores provide predictable state updates with minimal boilerplate
- **Real-time Capabilities**: SSE streams enable seamless live updates across all features
- **Clean Dependencies**: Features communicate through shared services rather than direct coupling
- **Performance Optimizations**: Caching, lazy loading, and efficient change detection ensure smooth user interactions

This architecture supports future growth by allowing new features to be added without disrupting existing functionality, while maintaining consistent patterns for state management and user interaction.