from __future__ import annotations

from app.agent.action_contracts import (
    AgentActionExecutionResult,
    AgentActionHandlerResult,
    AgentActionPreparation,
    AgentActionProposal,
)
from app.workplace_resources.workflows import WorkplaceWorkflowService


class OnboardOrganizationUserWorkflowHandler:
    requires_execution_context = True

    def __init__(self, service: WorkplaceWorkflowService) -> None:
        self._service = service

    async def prepare(
        self,
        *,
        organization_id: str,
        arguments: dict[str, str],
    ) -> AgentActionPreparation:
        return await self._service.prepare_onboard(
            organization_id=organization_id,
            arguments=arguments,
        )

    async def execute(
        self,
        *,
        proposal: AgentActionProposal,
        context,
    ) -> AgentActionHandlerResult:
        try:
            return await self._service.execute_onboard(
                proposal=proposal,
                executor_user_id=context.executed_by_user_id,
            )
        except Exception:
            await self._service.rollback()
            raise

    async def reconcile(
        self,
        *,
        proposal: AgentActionProposal,
        execution: AgentActionExecutionResult,
        context,
    ) -> AgentActionHandlerResult | None:
        return await self._service.reconcile_onboard(proposal=proposal)


class OffboardOrganizationUserWorkflowHandler:
    requires_execution_context = True

    def __init__(self, service: WorkplaceWorkflowService) -> None:
        self._service = service

    async def prepare(
        self,
        *,
        organization_id: str,
        arguments: dict[str, str],
    ) -> AgentActionPreparation:
        return await self._service.prepare_offboard(
            organization_id=organization_id,
            arguments=arguments,
        )

    async def execute(
        self,
        *,
        proposal: AgentActionProposal,
        context,
    ) -> AgentActionHandlerResult:
        try:
            return await self._service.execute_offboard(
                proposal=proposal,
                executor_user_id=context.executed_by_user_id,
            )
        except Exception:
            await self._service.rollback()
            raise

    async def reconcile(
        self,
        *,
        proposal: AgentActionProposal,
        execution: AgentActionExecutionResult,
        context,
    ) -> AgentActionHandlerResult | None:
        return await self._service.reconcile_offboard(proposal=proposal)


class ApplyOrganizationAccessPackageWorkflowHandler:
    requires_execution_context = True
    requires_nucleus_actor = True

    def __init__(self, service: WorkplaceWorkflowService) -> None:
        self._service = service

    async def prepare(
        self,
        *,
        organization_id: str,
        arguments: dict[str, str],
    ) -> AgentActionPreparation:
        return await self._service.prepare_access_package(
            organization_id=organization_id,
            arguments=arguments,
        )

    async def execute(
        self,
        *,
        proposal: AgentActionProposal,
        context,
    ) -> AgentActionHandlerResult:
        try:
            return await self._service.execute_access_package(
                proposal=proposal,
                nucleus_actor_id=context.nucleus_actor_id,
            )
        except Exception:
            await self._service.rollback()
            raise

    async def reconcile(
        self,
        *,
        proposal: AgentActionProposal,
        execution: AgentActionExecutionResult,
        context,
    ) -> AgentActionHandlerResult | None:
        return await self._service.reconcile_access_package(proposal=proposal)


class QuerySelectedBulkUpdateWorkflowHandler:
    def __init__(self, service: WorkplaceWorkflowService) -> None:
        self._service = service

    async def prepare(
        self,
        *,
        organization_id: str,
        arguments: dict[str, str],
    ) -> AgentActionPreparation:
        return await self._service.prepare_query_bulk_update(
            organization_id=organization_id,
            arguments=arguments,
        )

    async def execute(
        self,
        *,
        proposal: AgentActionProposal,
    ) -> AgentActionHandlerResult:
        try:
            return await self._service.execute_query_bulk_update(proposal=proposal)
        except Exception:
            await self._service.rollback()
            raise

    async def reconcile(
        self,
        *,
        proposal: AgentActionProposal,
        execution: AgentActionExecutionResult,
    ) -> AgentActionHandlerResult | None:
        return await self._service.reconcile_query_bulk_update(proposal=proposal)


class RestoreWorkplaceResourceSnapshotsHandler:
    """Internal-only rollback handler; this action is never offered to the model."""

    def __init__(self, service: WorkplaceWorkflowService) -> None:
        self._service = service

    async def prepare(
        self,
        *,
        organization_id: str,
        arguments: dict[str, str],
    ) -> AgentActionPreparation:
        return await self._service.prepare_snapshot_restore(
            organization_id=organization_id,
            arguments=arguments,
        )

    async def execute(
        self,
        *,
        proposal: AgentActionProposal,
    ) -> AgentActionHandlerResult:
        try:
            return await self._service.execute_snapshot_restore(proposal=proposal)
        except Exception:
            await self._service.rollback()
            raise

    async def reconcile(
        self,
        *,
        proposal: AgentActionProposal,
        execution: AgentActionExecutionResult,
    ) -> AgentActionHandlerResult | None:
        return await self._service.reconcile_snapshot_restore(proposal=proposal)
