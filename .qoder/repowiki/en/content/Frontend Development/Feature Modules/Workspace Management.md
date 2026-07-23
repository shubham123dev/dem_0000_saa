# Workspace Management

<cite>
**Referenced Files in This Document**
- [workspace-dashboard.component.ts](file://frontend/src/app/layout/workspace/workspace-dashboard.component.ts)
- [workspace-dashboard.component.html](file://frontend/src/app/layout/workspace/workspace-dashboard.component.html)
- [workspace-dashboard.component.scss](file://frontend/src/app/layout/workspace/workspace-dashboard.component.scss)
- [organization-workspace.component.ts](file://frontend/src/app/layout/workspace/organization-workspace.component.ts)
- [section-view.component.ts](file://frontend/src/app/layout/workspace/section-view.component.ts)
- [chat-view.component.ts](file://frontend/src/app/layout/workspace/chat-view.component.ts)
- [app.routes.ts](file://frontend/src/app/app.routes.ts)
- [shell-state.service.ts](file://frontend/src/app/layout/shell/shell-state.service.ts)
- [primary-sidebar.component.ts](file://frontend/src/app/layout/primary-sidebar/primary-sidebar.component.ts)
- [global-header.component.ts](file://frontend/src/app/layout/global-header/global-header.component.ts)
- [auth.guard.ts](file://frontend/src/app/core/routing/auth.guard.ts)
- [organization-route.service.ts](file://frontend/src/app/core/routing/organization-route.service.ts)
- [conversation-api.service.ts](file://frontend/src/app/core/conversation/conversation-api.service.ts)
- [workplace-agent-api.service.ts](file://frontend/src/app/core/api/workplace-agent-api.service.ts)
- [agent-conversation.store.ts](file://frontend/src/app/features/assistant-conversation/agent-conversation.store.ts)
- [conversation-list.component.ts](file://frontend/src/app/features/conversation-list/conversation-list.component.ts)
- [nucleus_organization_repository.py](file://app/repositories/nucleus_organization_repository.py)
- [organization_service.py](file://app/services/organization_service.py)
- [workplace_resource_routes.py](file://app/api/workplace_resource_routes.py)
- [workplace_routes.py](file://app/api/workplace_routes.py)
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
This document explains the Workspace Management feature, focusing on multi-organization navigation and overview, workspace components for context switching between organizations, chat view integration within workspaces, and section view management for organizing workspace content. It also covers workspace state synchronization, organization boundary enforcement, resource isolation patterns, examples for extending workspace views, implementing organization-specific features, managing cross-workspace data access, and performance considerations including lazy loading strategies for large organizations.

## Project Structure
The Workspace Management feature spans frontend shell layout, routing guards, stores, and API services, as well as backend repositories and routes that enforce organization boundaries and provide scoped resources.

```mermaid
graph TB
subgraph "Frontend Shell"
A["App Routes<br/>app.routes.ts"]
B["Shell State Service<br/>shell-state.service.ts"]
C["Primary Sidebar<br/>primary-sidebar.component.ts"]
D["Global Header<br/>global-header.component.ts"]
end
subgraph "Workspace Layout"
E["Organization Workspace<br/>organization-workspace.component.ts"]
F["Workspace Dashboard<br/>workspace-dashboard.component.*"]
G["Section View<br/>section-view.component.ts"]
H["Chat View<br/>chat-view.component.ts"]
end
subgraph "Conversation & API"
I["Agent Conversation Store<br/>agent-conversation.store.ts"]
J["Conversation API Service<br/>conversation-api.service.ts"]
K["Workplace Agent API Service<br/>workplace-agent-api.service.ts"]
end
subgraph "Routing Guards"
L["Auth Guard<br/>auth.guard.ts"]
M["Organization Route Service<br/>organization-route.service.ts"]
end
subgraph "Backend"
N["Nucleus Organization Repository<br/>nucleus_organization_repository.py"]
O["Organization Service<br/>organization_service.py"]
P["Workplace Resource Routes<br/>workplace_resource_routes.py"]
Q["Workplace Routes<br/>workplace_routes.py"]
end
A --> E
A --> F
A --> G
A --> H
E --> F
E --> G
E --> H
C --> E
D --> E
B --> E
E --> I
I --> J
I --> K
A --> L
A --> M
J --> P
K --> Q
O --> N
```

**Diagram sources**
- [app.routes.ts](file://frontend/src/app/app.routes.ts)
- [shell-state.service.ts](file://frontend/src/app/layout/shell/shell-state.service.ts)
- [primary-sidebar.component.ts](file://frontend/src/app/layout/primary-sidebar/primary-sidebar.component.ts)
- [global-header.component.ts](file://frontend/src/app/layout/global-header/global-header.component.ts)
- [organization-workspace.component.ts](file://frontend/src/app/layout/workspace/organization-workspace.component.ts)
- [workspace-dashboard.component.ts](file://frontend/src/app/layout/workspace/workspace-dashboard.component.ts)
- [section-view.component.ts](file://frontend/src/app/layout/workspace/section-view.component.ts)
- [chat-view.component.ts](file://frontend/src/app/layout/workspace/chat-view.component.ts)
- [agent-conversation.store.ts](file://frontend/src/app/features/assistant-conversation/agent-conversation.store.ts)
- [conversation-api.service.ts](file://frontend/src/app/core/conversation/conversation-api.service.ts)
- [workplace-agent-api.service.ts](file://frontend/src/app/core/api/workplace-agent-api.service.ts)
- [auth.guard.ts](file://frontend/src/app/core/routing/auth.guard.ts)
- [organization-route.service.ts](file://frontend/src/app/core/routing/organization-route.service.ts)
- [nucleus_organization_repository.py](file://app/repositories/nucleus_organization_repository.py)
- [organization_service.py](file://app/services/organization_service.py)
- [workplace_resource_routes.py](file://app/api/workplace_resource_routes.py)
- [workplace_routes.py](file://app/api/workplace_routes.py)

**Section sources**
- [app.routes.ts](file://frontend/src/app/app.routes.ts)
- [shell-state.service.ts](file://frontend/src/app/layout/shell/shell-state.service.ts)
- [primary-sidebar.component.ts](file://frontend/src/app/layout/primary-sidebar/primary-sidebar.component.ts)
- [global-header.component.ts](file://frontend/src/app/layout/global-header/global-header.component.ts)
- [organization-workspace.component.ts](file://frontend/src/app/layout/workspace/organization-workspace.component.ts)
- [workspace-dashboard.component.ts](file://frontend/src/app/layout/workspace/workspace-dashboard.component.ts)
- [section-view.component.ts](file://frontend/src/app/layout/workspace/section-view.component.ts)
- [chat-view.component.ts](file://frontend/src/app/layout/workspace/chat-view.component.ts)
- [agent-conversation.store.ts](file://frontend/src/app/features/assistant-conversation/agent-conversation.store.ts)
- [conversation-api.service.ts](file://frontend/src/app/core/conversation/conversation-api.service.ts)
- [workplace-agent-api.service.ts](file://frontend/src/app/core/api/workplace-agent-api.service.ts)
- [auth.guard.ts](file://frontend/src/app/core/routing/auth.guard.ts)
- [organization-route.service.ts](file://frontend/src/app/core/routing/organization-route.service.ts)
- [nucleus_organization_repository.py](file://app/repositories/nucleus_organization_repository.py)
- [organization_service.py](file://app/services/organization_service.py)
- [workplace_resource_routes.py](file://app/api/workplace_resource_routes.py)
- [workplace_routes.py](file://app/api/workplace_routes.py)

## Core Components
- Organization Workspace: Hosts the active organization context and composes dashboard, sections, and chat views. It ensures all child views operate under a single organization scope.
- Workspace Dashboard: Provides an overview of the current organization’s resources and quick actions. It is the default landing view when entering a workspace.
- Section View: Manages organized content areas (sections) within a workspace, enabling grouping and navigation of related items.
- Chat View: Integrates assistant conversations within the selected workspace, ensuring messages and proposals are scoped to the active organization.
- Routing Guards: Auth guard enforces authentication; organization route service validates and normalizes organization context before rendering workspace views.
- Shell State Service: Centralizes UI state such as sidebar visibility and panel sizes, shared across workspace views.
- Primary Sidebar and Global Header: Provide global navigation and organization selection controls that drive workspace context changes.

Key responsibilities:
- Maintain a consistent organization context across views.
- Isolate data access per organization via API calls with organization identifiers.
- Synchronize UI state and conversation state with the active workspace.

**Section sources**
- [organization-workspace.component.ts](file://frontend/src/app/layout/workspace/organization-workspace.component.ts)
- [workspace-dashboard.component.ts](file://frontend/src/app/layout/workspace/workspace-dashboard.component.ts)
- [workspace-dashboard.component.html](file://frontend/src/app/layout/workspace/workspace-dashboard.component.html)
- [workspace-dashboard.component.scss](file://frontend/src/app/layout/workspace/workspace-dashboard.component.scss)
- [section-view.component.ts](file://frontend/src/app/layout/workspace/section-view.component.ts)
- [chat-view.component.ts](file://frontend/src/app/layout/workspace/chat-view.component.ts)
- [auth.guard.ts](file://frontend/src/app/core/routing/auth.guard.ts)
- [organization-route.service.ts](file://frontend/src/app/core/routing/organization-route.service.ts)
- [shell-state.service.ts](file://frontend/src/app/layout/shell/shell-state.service.ts)
- [primary-sidebar.component.ts](file://frontend/src/app/layout/primary-sidebar/primary-sidebar.component.ts)
- [global-header.component.ts](file://frontend/src/app/layout/global-header/global-header.component.ts)

## Architecture Overview
The workspace architecture separates concerns into shell layout, workspace composition, conversation state, and API services, backed by backend repositories and routes that enforce organization boundaries.

```mermaid
sequenceDiagram
participant User as "User"
participant Router as "App Routes"
participant Guard as "Auth Guard"
participant OrgRoute as "Organization Route Service"
participant Workspace as "Organization Workspace"
participant Dashboard as "Workspace Dashboard"
participant Sections as "Section View"
participant Chat as "Chat View"
participant Store as "Agent Conversation Store"
participant ConvAPI as "Conversation API Service"
participant WorkplaceAPI as "Workplace Agent API Service"
participant Backend as "Backend Routes"
User->>Router : Navigate to /org/ : id
Router->>Guard : canActivate()
Guard-->>Router : Allow if authenticated
Router->>OrgRoute : Resolve org context
OrgRoute-->>Router : Validated organization id
Router->>Workspace : Render organization workspace
Workspace->>Dashboard : Load overview
Workspace->>Sections : Initialize sections
Workspace->>Chat : Initialize chat view
Chat->>Store : Subscribe to conversation state
Store->>ConvAPI : Fetch conversations scoped to org
Store->>WorkplaceAPI : Request workplace resources scoped to org
ConvAPI->>Backend : GET /api/conversations?org_id=...
WorkplaceAPI->>Backend : GET /api/workplace/resources?org_id=...
Backend-->>Store : Scoped data
Store-->>Chat : Update UI state
```

**Diagram sources**
- [app.routes.ts](file://frontend/src/app/app.routes.ts)
- [auth.guard.ts](file://frontend/src/app/core/routing/auth.guard.ts)
- [organization-route.service.ts](file://frontend/src/app/core/routing/organization-route.service.ts)
- [organization-workspace.component.ts](file://frontend/src/app/layout/workspace/organization-workspace.component.ts)
- [workspace-dashboard.component.ts](file://frontend/src/app/layout/workspace/workspace-dashboard.component.ts)
- [section-view.component.ts](file://frontend/src/app/layout/workspace/section-view.component.ts)
- [chat-view.component.ts](file://frontend/src/app/layout/workspace/chat-view.component.ts)
- [agent-conversation.store.ts](file://frontend/src/app/features/assistant-conversation/agent-conversation.store.ts)
- [conversation-api.service.ts](file://frontend/src/app/core/conversation/conversation-api.service.ts)
- [workplace-agent-api.service.ts](file://frontend/src/app/core/api/workplace-agent-api.service.ts)
- [workplace_resource_routes.py](file://app/api/workplace_resource_routes.py)
- [workplace_routes.py](file://app/api/workplace_routes.py)

## Detailed Component Analysis

### Organization Workspace
- Purpose: Establishes and maintains the active organization context for nested views. Ensures all child components receive the correct organization identifier.
- Responsibilities:
  - Validate and normalize organization context from route parameters.
  - Compose dashboard, sections, and chat views within the same organization scope.
  - Coordinate lifecycle events (init, destroy) to clean up subscriptions and caches.
- Integration Points:
  - Uses routing guards to ensure user is authenticated and has valid organization access.
  - Shares shell state for UI consistency.

```mermaid
classDiagram
class OrganizationWorkspace {
+activeOrgId : string
+initializeContext()
+composeViews()
+cleanup()
}
class WorkspaceDashboard {
+loadOverview()
+renderQuickActions()
}
class SectionView {
+listSections()
+selectSection(id)
}
class ChatView {
+subscribeToConversations()
+sendMessage(text)
}
OrganizationWorkspace --> WorkspaceDashboard : "composes"
OrganizationWorkspace --> SectionView : "composes"
OrganizationWorkspace --> ChatView : "composes"
```

**Diagram sources**
- [organization-workspace.component.ts](file://frontend/src/app/layout/workspace/organization-workspace.component.ts)
- [workspace-dashboard.component.ts](file://frontend/src/app/layout/workspace/workspace-dashboard.component.ts)
- [section-view.component.ts](file://frontend/src/app/layout/workspace/section-view.component.ts)
- [chat-view.component.ts](file://frontend/src/app/layout/workspace/chat-view.component.ts)

**Section sources**
- [organization-workspace.component.ts](file://frontend/src/app/layout/workspace/organization-workspace.component.ts)

### Workspace Dashboard
- Purpose: Presents an overview of the current organization’s resources and provides quick actions.
- Responsibilities:
  - Load organization-scoped metrics and resources.
  - Render summary cards and navigation shortcuts.
  - Handle user interactions to navigate to specific sections or open chats.
- Styling and Templates:
  - Uses dedicated HTML template and SCSS styles for layout and theming.

```mermaid
flowchart TD
Start(["Dashboard Init"]) --> LoadData["Load Organization Overview Data"]
LoadData --> HasData{"Data Loaded?"}
HasData --> |No| ShowSkeleton["Show Skeleton Placeholders"]
HasData --> |Yes| RenderCards["Render Summary Cards"]
RenderCards --> Actions["Bind Quick Actions"]
Actions --> End(["Ready"])
ShowSkeleton --> End
```

**Diagram sources**
- [workspace-dashboard.component.ts](file://frontend/src/app/layout/workspace/workspace-dashboard.component.ts)
- [workspace-dashboard.component.html](file://frontend/src/app/layout/workspace/workspace-dashboard.component.html)
- [workspace-dashboard.component.scss](file://frontend/src/app/layout/workspace/workspace-dashboard.component.scss)

**Section sources**
- [workspace-dashboard.component.ts](file://frontend/src/app/layout/workspace/workspace-dashboard.component.ts)
- [workspace-dashboard.component.html](file://frontend/src/app/layout/workspace/workspace-dashboard.component.html)
- [workspace-dashboard.component.scss](file://frontend/src/app/layout/workspace/workspace-dashboard.component.scss)

### Section View
- Purpose: Organizes workspace content into logical sections, enabling users to browse and select content groups.
- Responsibilities:
  - List available sections for the active organization.
  - Manage selection state and trigger content updates in dependent views.
  - Support lazy loading of section details when expanded.

```mermaid
sequenceDiagram
participant User as "User"
participant SectionView as "Section View"
participant Store as "Agent Conversation Store"
participant API as "Workplace Agent API Service"
participant Backend as "Backend Routes"
User->>SectionView : Click section
SectionView->>Store : Set selected section id
Store->>API : Fetch section resources (org-scoped)
API->>Backend : GET /api/workplace/resources?org_id=...&section=...
Backend-->>API : Section resources
API-->>Store : Resources payload
Store-->>SectionView : Update UI
```

**Diagram sources**
- [section-view.component.ts](file://frontend/src/app/layout/workspace/section-view.component.ts)
- [agent-conversation.store.ts](file://frontend/src/app/features/assistant-conversation/agent-conversation.store.ts)
- [workplace-agent-api.service.ts](file://frontend/src/app/core/api/workplace-agent-api.service.ts)
- [workplace_resource_routes.py](file://app/api/workplace_resource_routes.py)

**Section sources**
- [section-view.component.ts](file://frontend/src/app/layout/workspace/section-view.component.ts)

### Chat View
- Purpose: Integrates assistant conversations within the selected workspace, ensuring messages and proposals are scoped to the active organization.
- Responsibilities:
  - Subscribe to conversation state and render messages.
  - Send new messages and handle responses.
  - Ensure all conversation operations include the active organization context.

```mermaid
sequenceDiagram
participant User as "User"
participant ChatView as "Chat View"
participant Store as "Agent Conversation Store"
participant ConvAPI as "Conversation API Service"
participant Backend as "Backend Routes"
User->>ChatView : Type message
ChatView->>Store : Dispatch send message action
Store->>ConvAPI : POST /api/conversations/messages?org_id=...
ConvAPI->>Backend : Create message scoped to org
Backend-->>ConvAPI : Message created
ConvAPI-->>Store : Stream updates
Store-->>ChatView : Append message to UI
```

**Diagram sources**
- [chat-view.component.ts](file://frontend/src/app/layout/workspace/chat-view.component.ts)
- [agent-conversation.store.ts](file://frontend/src/app/features/assistant-conversation/agent-conversation.store.ts)
- [conversation-api.service.ts](file://frontend/src/app/core/conversation/conversation-api.service.ts)
- [workplace_routes.py](file://app/api/workplace_routes.py)

**Section sources**
- [chat-view.component.ts](file://frontend/src/app/layout/workspace/chat-view.component.ts)
- [agent-conversation.store.ts](file://frontend/src/app/features/assistant-conversation/agent-conversation.store.ts)
- [conversation-api.service.ts](file://frontend/src/app/core/conversation/conversation-api.service.ts)
- [workplace_routes.py](file://app/api/workplace_routes.py)

### Routing Guards and Context Resolution
- Auth Guard: Ensures only authenticated users can access workspace routes.
- Organization Route Service: Resolves and validates organization context from route parameters, preventing invalid or unauthorized organization access.

```mermaid
flowchart TD
Enter(["Navigate to /org/:id"]) --> CheckAuth["Check Authentication"]
CheckAuth --> AuthOK{"Authenticated?"}
AuthOK --> |No| RedirectLogin["Redirect to Login"]
AuthOK --> |Yes| ResolveOrg["Resolve Organization Context"]
ResolveOrg --> OrgValid{"Valid Organization?"}
OrgValid --> |No| NotFound["Show Not Found / Access Denied"]
OrgValid --> |Yes| Proceed["Proceed to Workspace"]
```

**Diagram sources**
- [auth.guard.ts](file://frontend/src/app/core/routing/auth.guard.ts)
- [organization-route.service.ts](file://frontend/src/app/core/routing/organization-route.service.ts)

**Section sources**
- [auth.guard.ts](file://frontend/src/app/core/routing/auth.guard.ts)
- [organization-route.service.ts](file://frontend/src/app/core/routing/organization-route.service.ts)

### Shell State and Navigation
- Shell State Service: Centralizes UI state like sidebar visibility and panel sizes, ensuring consistent behavior across workspace views.
- Primary Sidebar: Provides navigation links and organization selection controls.
- Global Header: Displays current organization context and offers quick actions.

```mermaid
classDiagram
class ShellStateService {
+sidebarVisible : boolean
+toggleSidebar()
+setPanelSize(size)
}
class PrimarySidebar {
+navigateTo(path)
+switchOrganization(orgId)
}
class GlobalHeader {
+showCurrentOrg()
+openSettings()
}
PrimarySidebar --> ShellStateService : "updates"
GlobalHeader --> ShellStateService : "reads/writes"
```

**Diagram sources**
- [shell-state.service.ts](file://frontend/src/app/layout/shell/shell-state.service.ts)
- [primary-sidebar.component.ts](file://frontend/src/app/layout/primary-sidebar/primary-sidebar.component.ts)
- [global-header.component.ts](file://frontend/src/app/layout/global-header/global-header.component.ts)

**Section sources**
- [shell-state.service.ts](file://frontend/src/app/layout/shell/shell-state.service.ts)
- [primary-sidebar.component.ts](file://frontend/src/app/layout/primary-sidebar/primary-sidebar.component.ts)
- [global-header.component.ts](file://frontend/src/app/layout/global-header/global-header.component.ts)

## Dependency Analysis
The workspace feature depends on routing guards, shell state, and API services, which in turn call backend endpoints enforcing organization scoping.

```mermaid
graph TB
WS["Organization Workspace"]
Dash["Workspace Dashboard"]
Sec["Section View"]
Chat["Chat View"]
Store["Agent Conversation Store"]
ConvAPI["Conversation API Service"]
WorkAPI["Workplace Agent API Service"]
OrgRepo["Nucleus Organization Repository"]
OrgSvc["Organization Service"]
WResRoutes["Workplace Resource Routes"]
WRoutes["Workplace Routes"]
WS --> Dash
WS --> Sec
WS --> Chat
Chat --> Store
Store --> ConvAPI
Sec --> WorkAPI
ConvAPI --> WRoutes
WorkAPI --> WResRoutes
OrgSvc --> OrgRepo
```

**Diagram sources**
- [organization-workspace.component.ts](file://frontend/src/app/layout/workspace/organization-workspace.component.ts)
- [workspace-dashboard.component.ts](file://frontend/src/app/layout/workspace/workspace-dashboard.component.ts)
- [section-view.component.ts](file://frontend/src/app/layout/workspace/section-view.component.ts)
- [chat-view.component.ts](file://frontend/src/app/layout/workspace/chat-view.component.ts)
- [agent-conversation.store.ts](file://frontend/src/app/features/assistant-conversation/agent-conversation.store.ts)
- [conversation-api.service.ts](file://frontend/src/app/core/conversation/conversation-api.service.ts)
- [workplace-agent-api.service.ts](file://frontend/src/app/core/api/workplace-agent-api.service.ts)
- [nucleus_organization_repository.py](file://app/repositories/nucleus_organization_repository.py)
- [organization_service.py](file://app/services/organization_service.py)
- [workplace_resource_routes.py](file://app/api/workplace_resource_routes.py)
- [workplace_routes.py](file://app/api/workplace_routes.py)

**Section sources**
- [organization-workspace.component.ts](file://frontend/src/app/layout/workspace/organization-workspace.component.ts)
- [workspace-dashboard.component.ts](file://frontend/src/app/layout/workspace/workspace-dashboard.component.ts)
- [section-view.component.ts](file://frontend/src/app/layout/workspace/section-view.component.ts)
- [chat-view.component.ts](file://frontend/src/app/layout/workspace/chat-view.component.ts)
- [agent-conversation.store.ts](file://frontend/src/app/features/assistant-conversation/agent-conversation.store.ts)
- [conversation-api.service.ts](file://frontend/src/app/core/conversation/conversation-api.service.ts)
- [workplace-agent-api.service.ts](file://frontend/src/app/core/api/workplace-agent-api.service.ts)
- [nucleus_organization_repository.py](file://app/repositories/nucleus_organization_repository.py)
- [organization_service.py](file://app/services/organization_service.py)
- [workplace_resource_routes.py](file://app/api/workplace_resource_routes.py)
- [workplace_routes.py](file://app/api/workplace_routes.py)

## Performance Considerations
- Lazy Loading Strategies:
  - Defer loading of heavy dashboard metrics until the workspace is fully initialized.
  - Use pagination and virtualization for large lists in section views.
  - Load chat history incrementally (e.g., last N messages) and fetch older messages on demand.
- Caching:
  - Cache organization overview data and frequently accessed resources to reduce repeated network calls.
  - Implement cache invalidation on relevant write operations (e.g., sending a message).
- Concurrency Control:
  - Debounce rapid UI interactions (e.g., typing in chat) to avoid excessive requests.
  - Cancel in-flight requests when navigating away from a workspace to prevent memory leaks.
- Large Organizations:
  - Prefer server-side filtering and sorting to minimize payload sizes.
  - Use progressive disclosure for detailed section content.
  - Monitor and optimize database queries behind organization-scoped endpoints.

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
Common issues and resolutions:
- Unauthorized Access:
  - Symptom: Redirected to login or denied access when opening a workspace.
  - Action: Verify authentication token validity and organization membership.
- Invalid Organization Context:
  - Symptom: Not found or access denied after navigating to an organization URL.
  - Action: Confirm organization ID exists and user has permissions; check route resolution logic.
- Stale Data in Dashboard:
  - Symptom: Overview shows outdated metrics.
  - Action: Trigger refresh or implement cache invalidation on relevant mutations.
- Chat Messages Not Appearing:
  - Symptom: Sent messages do not show immediately.
  - Action: Ensure store subscription is active and SSE/websocket connections are established; verify org-scoped request headers.

**Section sources**
- [auth.guard.ts](file://frontend/src/app/core/routing/auth.guard.ts)
- [organization-route.service.ts](file://frontend/src/app/core/routing/organization-route.service.ts)
- [agent-conversation.store.ts](file://frontend/src/app/features/assistant-conversation/agent-conversation.store.ts)
- [conversation-api.service.ts](file://frontend/src/app/core/conversation/conversation-api.service.ts)

## Conclusion
The Workspace Management feature provides a robust foundation for multi-organization navigation, context-aware workspace views, integrated chat experiences, and organized content sections. By enforcing organization boundaries at both frontend routing and backend endpoints, it ensures resource isolation and secure access. The design supports extensibility through additional workspace views and organization-specific features, while performance optimizations and lazy loading strategies help maintain responsiveness for large organizations.

[No sources needed since this section summarizes without analyzing specific files]