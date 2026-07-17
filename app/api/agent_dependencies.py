from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.agent.answer_contracts import (
    AgentAnswerDraft,
    AgentAnswerGateway,
    AgentEvidenceItem,
)
from app.agent.contracts import AgentModelGateway, AgentPlan, AgentToolDefinition
from app.agent.errors import AgentModelUnavailableError
from app.agent.evidence import AgentEvidenceCompiler
from app.agent.orchestrator import ReadOnlyAgentOrchestrator
from app.agent.providers.openai_responses import OpenAIResponsesAgentModelGateway
from app.agent.response_service import ReadOnlyAgentResponseService
from app.agent.synthesis import AgentAnswerSynthesisService
from app.agent.tool_registry import ReadOnlyAgentToolRegistry
from app.api.dependencies import OrganizationServiceDep
from app.core.config import get_settings


class UnavailableAgentModelGateway:
    async def create_plan(
        self,
        *,
        user_request: str,
        available_tools: tuple[AgentToolDefinition, ...],
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


def get_read_only_agent_orchestrator(
    organization_service: OrganizationServiceDep,
    model_gateway: Annotated[AgentModelGateway, Depends(get_agent_model_gateway)],
    tool_registry: Annotated[
        ReadOnlyAgentToolRegistry,
        Depends(get_read_only_agent_tool_registry),
    ],
) -> ReadOnlyAgentOrchestrator:
    return ReadOnlyAgentOrchestrator(
        model_gateway=model_gateway,
        tool_registry=tool_registry,
        organization_service=organization_service,
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
) -> ReadOnlyAgentResponseService:
    return ReadOnlyAgentResponseService(
        orchestrator=orchestrator,
        evidence_compiler=evidence_compiler,
        synthesis_service=synthesis_service,
    )


ReadOnlyAgentOrchestratorDep = Annotated[
    ReadOnlyAgentOrchestrator,
    Depends(get_read_only_agent_orchestrator),
]
ReadOnlyAgentResponseServiceDep = Annotated[
    ReadOnlyAgentResponseService,
    Depends(get_read_only_agent_response_service),
]
