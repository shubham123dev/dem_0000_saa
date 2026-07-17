from __future__ import annotations

from app.agent.action_contracts import AgentActionProposal, AgentActionProposalInput
from app.agent.action_errors import (
    AgentActionRollbackUnavailableError,
    AgentActionStaleError,
)
from app.domain.models import User
from app.repositories.agent_action_repository import AgentActionTransitionConflictError
from app.services.agent_action_service import AgentActionService
from app.services.operational_resource_service import OperationalResourceNotFoundError


class StaleSafeAgentActionService(AgentActionService):
    """Harden resource drift and create rollback proposals through normal lifecycle."""

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

    async def create_rollback_proposal(
        self,
        *,
        user: User,
        organization_id: str,
        source_proposal_id: str,
        reason: str | None,
    ) -> AgentActionProposal:
        source = await self.get_proposal(
            user=user,
            organization_id=organization_id,
            proposal_id=source_proposal_id,
        )
        execution = await self._action_repository.get_execution(source.id)
        if execution is None or execution.outcome != "succeeded" or not execution.result:
            raise AgentActionRollbackUnavailableError()

        rollback_input = self._build_rollback_input(source, execution.result)
        rollback = await self.propose(
            user=user,
            organization_id=organization_id,
            proposal_input=rollback_input,
            provenance={
                "proposal_source": "rollback",
                "source_proposal_id": source.id,
                "reason": reason,
            },
        )
        try:
            await self._action_repository.create_rollback_link(
                source_proposal_id=source.id,
                rollback_proposal_id=rollback.id,
                created_by_user_id=user.id,
            )
        except (AttributeError, AgentActionTransitionConflictError) as exception:
            await self._action_repository.transition_status(
                proposal_id=rollback.id,
                current_statuses=("pending_approval",),
                target_status="cancelled",
            )
            raise AgentActionRollbackUnavailableError() from exception
        return rollback

    @staticmethod
    def _build_rollback_input(
        source: AgentActionProposal,
        result: dict,
    ) -> AgentActionProposalInput:
        before = dict(result.get("before") or {})
        after = dict(result.get("after") or {})
        arguments = source.arguments

        if source.action_name == "update_organization_contact_email":
            previous_email = before.get("contact_email")
            if not isinstance(previous_email, str) or not previous_email:
                raise AgentActionRollbackUnavailableError()
            return AgentActionProposalInput(
                action_name="update_organization_contact_email",
                arguments={"contact_email": previous_email},
            )

        if source.action_name == "invite_organization_user":
            user_id = after.get("user_id")
            if not isinstance(user_id, str) or not user_id:
                raise AgentActionRollbackUnavailableError()
            return AgentActionProposalInput(
                action_name="remove_organization_user",
                arguments={"user_id": user_id},
            )

        if source.action_name == "update_organization_member_role":
            previous_role = before.get("role")
            if not isinstance(previous_role, str) or not previous_role:
                raise AgentActionRollbackUnavailableError()
            return AgentActionProposalInput(
                action_name="update_organization_member_role",
                arguments={
                    "user_id": arguments["user_id"],
                    "role": previous_role,
                },
            )

        if source.action_name == "assign_organization_seat":
            return AgentActionProposalInput(
                action_name="revoke_organization_seat",
                arguments={
                    "user_id": arguments["user_id"],
                    "seat_type": arguments["seat_type"],
                },
            )

        if source.action_name == "revoke_organization_seat":
            return AgentActionProposalInput(
                action_name="assign_organization_seat",
                arguments={
                    "user_id": arguments["user_id"],
                    "seat_type": arguments["seat_type"],
                },
            )

        if source.action_name == "grant_organization_report_access":
            previous_status = before.get("status")
            previous_level = before.get("access_level")
            if previous_status == "active" and isinstance(previous_level, str):
                return AgentActionProposalInput(
                    action_name="grant_organization_report_access",
                    arguments={
                        "report_id": arguments["report_id"],
                        "access_level": previous_level,
                    },
                )
            return AgentActionProposalInput(
                action_name="revoke_organization_report_access",
                arguments={"report_id": arguments["report_id"]},
            )

        raise AgentActionRollbackUnavailableError()
