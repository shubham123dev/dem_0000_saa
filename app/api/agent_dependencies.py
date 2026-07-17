from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.agent.contracts import AgentModelGateway, AgentPlan, AgentToolDefinition
from app.agent.errors import AgentModelUnavailableError
from app.agent.orchestrator import ReadOnlyAgentOrchestrator
from app.agent.tool_registry import ReadOnlyAgentToolRegistry
from app.api.dependencies import OrganizationServiceDep


class UnavailableAgentModelGateway:
    async def create_plan(
        self,
        *,
        user_request: str,
        available_tools: tuple[AgentToolDefinition, ...],
    ) -> AgentPlan:
        raise AgentModelUnavailableError()


def get_agent_model_gateway() -> AgentModelGateway:
    return UnavailableAgentModelGateway()


def get_read_only_agent_tool_registry() -> ReadOnlyAgentToolRegistry:
    return ReadOnlyAgentToolRegistry()


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


ReadOnlyAgentOrchestratorDep = Annotated[
    ReadOnlyAgentOrchestrator,
    Depends(get_read_only_agent_orchestrator),
]
