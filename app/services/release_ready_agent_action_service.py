from __future__ import annotations

from app.agent.action_contracts import AgentActionProposal, AgentActionProposalInput
from app.agent.action_errors import AgentActionInvalidError
from app.agent.action_registry import InvalidAgentActionProposalError
from app.domain.enums import Permission
from app.domain.models import User
from app.services.hardened_agent_action_service import HardenedAgentActionService


class ReleaseReadyAgentActionService(HardenedAgentActionService):
    """Final authorization boundary for proposal-scoped operations.

    Action-management permissions control access to the lifecycle surface, while
    the selected action's permission still controls the underlying resource.
    Neither permission family can substitute for the other.
    """

    async def propose(
        self,
        *,
        user: User,
        organization_id: str,
        proposal_input: AgentActionProposalInput,
        provenance: dict | None = None,
    ) -> AgentActionProposal:
        try:
            definition = self._action_registry.validate(proposal_input)
        except InvalidAgentActionProposalError as exception:
            raise AgentActionInvalidError() from exception
        await self._authorize(
            user=user,
            organization_id=organization_id,
            required_permission=definition.required_permission,
        )
        # Authorization must precede limit evaluation to avoid leaking queue state.
        # The parent lifecycle intentionally rechecks permission immediately before
        # preparation and persistence so a concurrent permission revocation wins.
        return await super().propose(
            user=user,
            organization_id=organization_id,
            proposal_input=proposal_input,
            provenance=provenance,
        )

    async def get_proposal(
        self,
        *,
        user: User,
        organization_id: str,
        proposal_id: str,
    ) -> AgentActionProposal:
        await self._authorize(
            user=user,
            organization_id=organization_id,
            required_permission=Permission.AGENT_ACTIONS_READ.value,
        )
        proposal = await self._require_proposal(
            organization_id=organization_id,
            proposal_id=proposal_id,
        )
        action_definition = self._action_registry.get_definition(proposal.action_name)
        await self._authorize(
            user=user,
            organization_id=organization_id,
            required_permission=action_definition.required_permission,
        )
        return await self._expire_if_needed(proposal)
