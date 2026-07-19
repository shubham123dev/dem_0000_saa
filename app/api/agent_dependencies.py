from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.adapters.organization.mock_adapter import MockOrganizationApiAdapter
from app.agent.action_contracts import AgentActionDefinition
from app.agent.action_registry import AgentActionRegistry
from app.agent.answer_contracts import (
    AgentAnswerDraft,
    AgentAnswerGateway,
    AgentEvidenceItem,
)
from app.agent.contracts import AgentModelGateway, AgentPlan, AgentToolDefinition
from app.agent.errors import AgentModelUnavailableError
from app.agent.evidence import AgentEvidenceCompiler
from app.agent.orchestrator import ReadOnlyAgentOrchestrator
from app.agent.providers.workplace_openai_responses import OpenAIResponsesAgentModelGateway
from app.agent.response_service import ReadOnlyAgentResponseService
from app.agent.synthesis import AgentAnswerSynthesisService
from app.agent.tool_registry import ReadOnlyAgentToolRegistry
from app.api.action_dependencies import AgentActionServiceDep, get_agent_action_registry
from app.api.dependencies import (
    MockOrganizationApiDep,
    NucleusOrganizationServiceDep,
    OrganizationServiceDep,
    SessionDep,
    get_user_repository,
)
from app.core.config import get_settings
from app.permissions.permission_service import PermissionService
from app.repositories.user_repository import UserRepository
from app.services.agent_preflight_service import AgentAuthorizationPreflightService
from app.workplace_resources.advanced_query import WorkplaceAdvancedQueryService
from app.workplace_resources.operation_router import WorkplaceOperationRouter
from app.workplace_resources.relationships import WorkplaceRelationshipService
from app.workplace_resources.registry import WorkplaceResourceRegistry
from app.workplace_resources.service import WorkplaceResourceService


class UnavailableAgentModelGateway:
    async def create_plan(
        self,
        *,
        user_request: str,
        available_tools: tuple[AgentToolDefinition, ...],
        available_actions: tuple[AgentActionDefinition, ...],
    ) -> AgentPlan:
        raise AgentModelUnavailableError()

    async def create_answer(
        self,
        *,
        user_request: str,
        evidence: tuple[AgentEvidenceItem, ...],
    ) -> AgentAnswerDraft:
        raise AgentModelUnavailableError()


def _build_configured_gateway() -> OpenAIResponsesAgentModelGateway | None:
    settings = get_settings()
    if settings.agent_model_provider != "openai" or not settings.agent_model_api_key:
        return None
    return OpenAIResponsesAgentModelGateway(
        api_key=settings.agent_model_api_key,
        model=settings.agent_model_name,
        endpoint=settings.agent_model_endpoint,
        timeout_seconds=settings.agent_model_timeout_seconds,
        maximum_attempts=settings.agent_model_maximum_attempts,
        retry_delay_seconds=settings.agent_model_retry_delay_seconds,
        maximum_output_tokens=settings.agent_model_maximum_output_tokens,
    )


def get_agent_model_gateway() -> AgentModelGateway:
    return _build_configured_gateway() or UnavailableAgentModelGateway()


def get_agent_answer_gateway() -> AgentAnswerGateway:
    return _build_configured_gateway() or UnavailableAgentModelGateway()


def get_read_only_agent_tool_registry() -> ReadOnlyAgentToolRegistry:
    return ReadOnlyAgentToolRegistry()


def get_agent_evidence_compiler() -> AgentEvidenceCompiler:
    return AgentEvidenceCompiler()


def get_agent_authorization_preflight_service(
    api: MockOrganizationApiDep,
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> AgentAuthorizationPreflightService:
    return AgentAuthorizationPreflightService(
        organization_gateway=MockOrganizationApiAdapter(api),
        permission_service=PermissionService(user_repository),
    )


def get_read_only_agent_orchestrator(
    organization_service: OrganizationServiceDep,
    nucleus_organization_service: NucleusOrganizationServiceDep,
    session: SessionDep,
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    model_gateway: Annotated[AgentModelGateway, Depends(get_agent_model_gateway)],
    tool_registry: Annotated[
        ReadOnlyAgentToolRegistry,
        Depends(get_read_only_agent_tool_registry),
    ],
    action_registry: Annotated[
        AgentActionRegistry,
        Depends(get_agent_action_registry),
    ],
) -> ReadOnlyAgentOrchestrator:
    resource_registry = WorkplaceResourceRegistry()
    operation_router = WorkplaceOperationRouter(resource_registry)
    advanced_query_service = WorkplaceAdvancedQueryService(
        session,
        resource_registry,
    )
    relationship_service = WorkplaceRelationshipService(
        session,
        resource_registry,
        operation_router,
    )
    return ReadOnlyAgentOrchestrator(
        model_gateway=model_gateway,
        tool_registry=tool_registry,
        action_registry=action_registry,
        organization_service=organization_service,
        nucleus_organization_service=nucleus_organization_service,
        workplace_resource_service=WorkplaceResourceService(
            session,
            resource_registry,
        ),
        workplace_operation_router=operation_router,
        advanced_query_service=advanced_query_service,
        relationship_service=relationship_service,
        permission_service=PermissionService(user_repository),
    )


def get_agent_synthesis_service(
    answer_gateway: Annotated[AgentAnswerGateway, Depends(get_agent_answer_gateway)],
) -> AgentAnswerSynthesisService:
    return AgentAnswerSynthesisService(answer_gateway)


def get_read_only_agent_response_service(
    orchestrator: Annotated[
        ReadOnlyAgentOrchestrator,
        Depends(get_read_only_agent_orchestrator),
    ],
    evidence_compiler: Annotated[
        AgentEvidenceCompiler,
        Depends(get_agent_evidence_compiler),
    ],
    synthesis_service: Annotated[
        AgentAnswerSynthesisService,
        Depends(get_agent_synthesis_service),
    ],
    action_service: AgentActionServiceDep,
    preflight_service: Annotated[
        AgentAuthorizationPreflightService,
        Depends(get_agent_authorization_preflight_service),
    ],
) -> ReadOnlyAgentResponseService:
    return ReadOnlyAgentResponseService(
        orchestrator=orchestrator,
        evidence_compiler=evidence_compiler,
        synthesis_service=synthesis_service,
        action_service=action_service,
        preflight_service=preflight_service,
        operation_router=WorkplaceOperationRouter(),
    )


ReadOnlyAgentOrchestratorDep = Annotated[
    ReadOnlyAgentOrchestrator,
    Depends(get_read_only_agent_orchestrator),
]
ReadOnlyAgentResponseServiceDep = Annotated[
    ReadOnlyAgentResponseService,
    Depends(get_read_only_agent_response_service),
]
