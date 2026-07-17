from __future__ import annotations

from app.agent.action_errors import AgentActionStaleError
from app.domain.models import User
from app.services.agent_action_service import AgentActionService
from app.services.operational_resource_service import OperationalResourceNotFoundError


class StaleSafeAgentActionService(AgentActionService):
    """Preserve the base lifecycle while normalizing pre-execution drift.

    Proposal creation intentionally surfaces validation failures as invalid action
    requests. During execution, however, the same handler validation may fail
    because the reviewed resource changed after approval. Such drift is a stale
    proposal, not an internal server error.
    """

    async def execute(
        self,
        *,
        user: User,
        organization_id: str,
        proposal_id: str,
        idempotency_key: str,
    ):
        try:
            return await super().execute(
                user=user,
                organization_id=organization_id,
                proposal_id=proposal_id,
                idempotency_key=idempotency_key,
            )
        except (KeyError, ValueError, OperationalResourceNotFoundError) as exception:
            proposal = await self._action_repository.get_proposal(
                proposal_id=proposal_id,
                organization_id=organization_id,
            )
            if proposal is None or proposal.status != "approved":
                raise
            await self._action_repository.transition_status(
                proposal_id=proposal.id,
                current_statuses=("approved",),
                target_status="stale",
            )
            raise AgentActionStaleError() from exception
