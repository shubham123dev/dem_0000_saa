from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.organization.mock_adapter import MockOrganizationApiAdapter
from app.agent.instrumented_orchestrator import InstrumentedReadOnlyAgentOrchestrator
from app.agent.response_service import ReadOnlyAgentResponseService
from app.api.action_dependencies import (
    get_agent_action_handlers,
    get_agent_action_repository,
    get_agent_action_registry,
    get_agent_action_service,
)
from app.api.agent_dependencies import (
    get_agent_answer_gateway,
    get_agent_authorization_preflight_service,
    get_agent_evidence_compiler,
    get_agent_model_gateway,
    get_agent_synthesis_service,
    get_read_only_agent_tool_registry,
)
from app.api.dependencies import (
    get_audit_repository,
    get_nucleus_organization_repository,
    get_nucleus_organization_service,
    get_organization_service,
    get_user_repository,
)
from app.mock_api.service import MockOrganizationApi
from app.permissions.permission_service import PermissionService
from app.services.agent_run_activity import DatabaseAgentRunActivitySink
from app.workplace_resources.advanced_query import WorkplaceAdvancedQueryService
from app.workplace_resources.operation_router import WorkplaceOperationRouter
from app.workplace_resources.relationships import WorkplaceRelationshipService
from app.workplace_resources.registry import WorkplaceResourceRegistry
from app.workplace_resources.service import WorkplaceResourceService


def build_run_response_service(
    session: AsyncSession,
    *,
    activity_sink: DatabaseAgentRunActivitySink,
) -> ReadOnlyAgentResponseService:
    user_repository = get_user_repository(session)
    audit_repository = get_audit_repository(session)
    mock_api = MockOrganizationApi(session)
    organization_gateway = MockOrganizationApiAdapter(mock_api)
    nucleus_gateway = get_nucleus_organization_repository(session)
    organization_service = get_organization_service(
        organization_gateway,
        user_repository,
        audit_repository,
    )
    nucleus_service = get_nucleus_organization_service(
        organization_gateway,
        user_repository,
        audit_repository,
        nucleus_gateway,
    )
    action_registry = get_agent_action_registry()
    action_repository = get_agent_action_repository(session)
    action_handlers = get_agent_action_handlers(
        session,
        nucleus_gateway,
        organization_gateway,
    )
    action_service = get_agent_action_service(
        organization_gateway,
        user_repository,
        audit_repository,
        session,
        action_repository,
        action_registry,
        action_handlers,
    )
    resource_registry = WorkplaceResourceRegistry()
    operation_router = WorkplaceOperationRouter(resource_registry)
    orchestrator = InstrumentedReadOnlyAgentOrchestrator(
        model_gateway=get_agent_model_gateway(),
        tool_registry=get_read_only_agent_tool_registry(),
        action_registry=action_registry,
        organization_service=organization_service,
        nucleus_organization_service=nucleus_service,
        workplace_resource_service=WorkplaceResourceService(
            session,
            resource_registry,
        ),
        workplace_operation_router=operation_router,
        advanced_query_service=WorkplaceAdvancedQueryService(
            session,
            resource_registry,
        ),
        relationship_service=WorkplaceRelationshipService(
            session,
            resource_registry,
            operation_router,
        ),
        permission_service=PermissionService(user_repository),
        activity_sink=activity_sink,
    )
    return ReadOnlyAgentResponseService(
        orchestrator=orchestrator,
        evidence_compiler=get_agent_evidence_compiler(),
        synthesis_service=get_agent_synthesis_service(get_agent_answer_gateway()),
        action_service=action_service,
        preflight_service=get_agent_authorization_preflight_service(
            mock_api,
            user_repository,
        ),
        operation_router=WorkplaceOperationRouter(),
        organization_service=organization_service,
        action_registry=action_registry,
    )
