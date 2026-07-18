from __future__ import annotations

from app.agent.action_contracts import (
    AgentActionExecutionResult,
    AgentActionHandlerResult,
    AgentActionPreparation,
    AgentActionProposal,
)
from app.workplace_resources.service import WorkplaceResourceService


class WorkplaceResourceActionHandler:
    requires_execution_context = True

    def __init__(
        self,
        service: WorkplaceResourceService,
        operation: str,
    ) -> None:
        self._service = service
        self._operation = operation

    async def prepare(
        self,
        *,
        organization_id: str,
        arguments: dict[str, str],
    ) -> AgentActionPreparation:
        return await self._service.prepare(
            organization_id=organization_id,
            operation=self._operation,
            arguments=arguments,
        )

    async def execute(
        self,
        *,
        proposal: AgentActionProposal,
        context,
    ) -> AgentActionHandlerResult:
        return await self._service.execute(
            proposal=proposal,
            operation=self._operation,
            executor_user_id=context.executed_by_user_id,
        )

    async def reconcile(
        self,
        *,
        proposal: AgentActionProposal,
        execution: AgentActionExecutionResult,
        context,
    ) -> AgentActionHandlerResult | None:
        return await self._service.reconcile(
            proposal=proposal,
            operation=self._operation,
        )
