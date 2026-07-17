from __future__ import annotations

from app.agent.action_contracts import AgentActionExecutionResult
from app.domain.models import User
from app.services.agent_action_service import AgentActionService


class AgentActionReconciliationService:
    def __init__(self, action_service: AgentActionService) -> None:
        self._action_service = action_service

    async def reconcile(
        self,
        *,
        user: User,
        organization_id: str,
        proposal_id: str,
    ) -> AgentActionExecutionResult:
        return await self._action_service.reconcile(
            user=user,
            organization_id=organization_id,
            proposal_id=proposal_id,
        )
