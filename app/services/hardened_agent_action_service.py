from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.agent.action_contracts import (
    AgentActionApproval,
    AgentActionExecutionResult,
    AgentActionProposal,
    AgentActionProposalInput,
)
from app.agent.action_errors import (
    AgentActionLimitExceededError,
    AgentActionStateConflictError,
)
from app.core.config import get_settings
from app.domain.enums import Permission
from app.domain.models import User
from app.repositories.hardened_agent_action_repository import (
    HardenedAgentActionRepository,
)
from app.services.stale_safe_agent_action_service import StaleSafeAgentActionService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class HardenedAgentActionService(StaleSafeAgentActionService):
    @property
    def _hardened_repository(self) -> HardenedAgentActionRepository:
        repository = self._action_repository
        if not isinstance(repository, HardenedAgentActionRepository):
            raise RuntimeError("Hardened action repository is not configured")
        return repository

    async def propose(
        self,
        *,
        user: User,
        organization_id: str,
        proposal_input: AgentActionProposalInput,
        provenance: dict | None = None,
    ) -> AgentActionProposal:
        settings = get_settings()
        repository = self._hardened_repository
        pending_organization = await repository.count_pending(
            organization_id=organization_id
        )
        if pending_organization >= settings.action_maximum_pending_per_organization:
            raise AgentActionLimitExceededError(
                "The organization has too many pending action proposals."
            )
        pending_user = await repository.count_pending(
            organization_id=organization_id,
            requested_by_user_id=user.id,
        )
        if pending_user >= settings.action_maximum_pending_per_user:
            raise AgentActionLimitExceededError(
                "The requester has too many pending action proposals."
            )
        recent = await repository.count_recent_proposals(
            organization_id=organization_id,
            requested_by_user_id=user.id,
            since=_utcnow() - timedelta(minutes=1),
        )
        if recent >= settings.action_maximum_proposals_per_user_per_minute:
            raise AgentActionLimitExceededError(
                "The requester proposal rate limit has been reached."
            )
        return await super().propose(
            user=user,
            organization_id=organization_id,
            proposal_input=proposal_input,
            provenance=provenance,
        )

    async def list_proposals_page(
        self,
        *,
        user: User,
        organization_id: str,
        status: str | None,
        action_name: str | None,
        requested_by_user_id: str | None,
        limit: int | None,
        cursor: str | None,
    ) -> tuple[tuple[AgentActionProposal, ...], str | None]:
        await self._authorize(
            user=user,
            organization_id=organization_id,
            required_permission=Permission.AGENT_ACTIONS_READ.value,
        )
        settings = get_settings()
        resolved_limit = limit or settings.action_default_page_size
        if resolved_limit > settings.action_maximum_page_size:
            raise AgentActionLimitExceededError("The requested page size is too large.")
        proposals, next_cursor = await self._hardened_repository.list_proposals_page(
            organization_id=organization_id,
            status=status,
            action_name=action_name,
            requested_by_user_id=requested_by_user_id,
            limit=resolved_limit,
            cursor=cursor,
        )
        refreshed = [await self._expire_if_needed(item) for item in proposals]
        return tuple(refreshed), next_cursor

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
        return await self._expire_if_needed(proposal)

    async def decide(
        self,
        *,
        user: User,
        organization_id: str,
        proposal_id: str,
        decision: str,
        reason: str | None,
    ) -> AgentActionApproval:
        await self._authorize(
            user=user,
            organization_id=organization_id,
            required_permission=Permission.AGENT_ACTIONS_APPROVE.value,
        )
        return await super().decide(
            user=user,
            organization_id=organization_id,
            proposal_id=proposal_id,
            decision=decision,
            reason=reason,
        )

    async def execute(
        self,
        *,
        user: User,
        organization_id: str,
        proposal_id: str,
        idempotency_key: str,
    ) -> AgentActionExecutionResult:
        await self._authorize(
            user=user,
            organization_id=organization_id,
            required_permission=Permission.AGENT_ACTIONS_EXECUTE.value,
        )
        return await super().execute(
            user=user,
            organization_id=organization_id,
            proposal_id=proposal_id,
            idempotency_key=idempotency_key,
        )

    async def reconcile(
        self,
        *,
        user: User,
        organization_id: str,
        proposal_id: str,
    ) -> AgentActionExecutionResult:
        await self._authorize(
            user=user,
            organization_id=organization_id,
            required_permission=Permission.AGENT_ACTIONS_RECONCILE.value,
        )
        execution = await self._hardened_repository.get_execution(proposal_id)
        settings = get_settings()
        if (
            execution is not None
            and execution.attempt_count >= settings.action_maximum_reconciliation_attempts
            and execution.outcome in {"executing", "reconciliation_required"}
        ):
            raise AgentActionLimitExceededError(
                "The reconciliation attempt limit has been reached."
            )
        return await super().reconcile(
            user=user,
            organization_id=organization_id,
            proposal_id=proposal_id,
        )

    async def create_rollback_proposal(
        self,
        *,
        user: User,
        organization_id: str,
        source_proposal_id: str,
        reason: str | None,
    ) -> AgentActionProposal:
        await self._authorize(
            user=user,
            organization_id=organization_id,
            required_permission=Permission.AGENT_ACTIONS_EXECUTE.value,
        )
        return await super().create_rollback_proposal(
            user=user,
            organization_id=organization_id,
            source_proposal_id=source_proposal_id,
            reason=reason,
        )

    async def replay_audit(
        self,
        *,
        user: User,
        organization_id: str,
        proposal_id: str,
    ) -> AgentActionExecutionResult:
        await self._authorize(
            user=user,
            organization_id=organization_id,
            required_permission=Permission.AGENT_ACTIONS_RECONCILE.value,
        )
        proposal = await self._require_proposal(
            organization_id=organization_id,
            proposal_id=proposal_id,
        )
        execution = await self._require_execution(proposal_id)
        if not execution.audit_pending:
            return execution
        settings = get_settings()
        pending = await self._hardened_repository.list_audit_pending_executions(
            limit=settings.action_maximum_page_size,
            maximum_attempts=settings.action_maximum_audit_replay_attempts,
        )
        if proposal_id not in {item.proposal_id for item in pending}:
            raise AgentActionLimitExceededError(
                "The audit replay attempt limit has been reached."
            )
        try:
            await self._audit_repository.append(
                actor_user_id=user.id,
                organization_id=organization_id,
                event_type="agent_action_audit_replayed",
                operation="write",
                outcome="success",
                resource_type=proposal.resource_type,
                resource_id=proposal.resource_id,
                details={
                    "proposal_id": proposal.id,
                    "action_name": proposal.action_name,
                    "execution_outcome": execution.outcome,
                    "replayed_at": _utcnow().isoformat(),
                },
            )
        except Exception as exception:
            await self._hardened_repository.record_audit_replay(
                proposal_id=proposal_id,
                success=False,
                error_code=type(exception).__name__[:200],
            )
            raise AgentActionStateConflictError(
                "The audit replay could not be persisted."
            ) from exception
        return await self._hardened_repository.record_audit_replay(
            proposal_id=proposal_id,
            success=True,
            error_code=None,
        )
