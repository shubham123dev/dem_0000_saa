from __future__ import annotations

from datetime import datetime, timezone
import uuid

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from app.agent.action_contracts import AgentActionApproval, AgentActionExecutionResult, AgentApprovalPolicy
from app.db.action_models import (
    AgentActionApprovalORM,
    AgentActionExecutionORM,
    AgentActionProposalORM,
    AgentActionRollbackORM,
)
from app.repositories.agent_action_repository import (
    AgentActionRepository,
    AgentActionTransitionConflictError,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class MultiApprovalAgentActionRepository(AgentActionRepository):
    async def list_approvals(self, proposal_id: str) -> tuple[AgentActionApproval, ...]:
        rows = (
            await self._session.execute(
                select(AgentActionApprovalORM)
                .where(AgentActionApprovalORM.proposal_id == proposal_id)
                .order_by(AgentActionApprovalORM.decided_at.asc())
            )
        ).scalars().all()
        return tuple(self._approval_to_domain(row) for row in rows)

    async def get_approval(self, proposal_id: str) -> AgentActionApproval | None:
        row = await self._session.scalar(
            select(AgentActionApprovalORM)
            .where(
                AgentActionApprovalORM.proposal_id == proposal_id,
                AgentActionApprovalORM.decision == "approved",
                AgentActionApprovalORM.consumed_at.is_(None),
            )
            .order_by(AgentActionApprovalORM.decided_at.asc())
        )
        return self._approval_to_domain(row) if row is not None else None

    async def decide(
        self,
        *,
        proposal_id: str,
        decided_by_user_id: str,
        decision: str,
        decision_reason: str | None,
    ) -> AgentActionApproval:
        now = _utcnow()
        proposal = await self._session.scalar(
            select(AgentActionProposalORM)
            .where(AgentActionProposalORM.id == proposal_id)
            .with_for_update()
        )
        if (
            proposal is None
            or proposal.status != "pending_approval"
            or _as_aware(proposal.expires_at) <= now
        ):
            await self._session.rollback()
            raise AgentActionTransitionConflictError()

        approval = AgentActionApprovalORM(
            id=uuid.uuid4().hex,
            proposal_id=proposal_id,
            decision=decision,
            decided_by_user_id=decided_by_user_id,
            decision_reason=decision_reason,
            decided_at=now,
        )
        self._session.add(approval)
        try:
            await self._session.flush()
        except IntegrityError as exception:
            await self._session.rollback()
            raise AgentActionTransitionConflictError() from exception

        if decision == "rejected":
            proposal.status = "rejected"
            proposal.updated_at = now
        else:
            policy = AgentApprovalPolicy.model_validate(proposal.approval_policy_json)
            approved_count = int(
                await self._session.scalar(
                    select(func.count())
                    .select_from(AgentActionApprovalORM)
                    .where(
                        AgentActionApprovalORM.proposal_id == proposal_id,
                        AgentActionApprovalORM.decision == "approved",
                    )
                )
                or 0
            )
            if approved_count >= policy.minimum_approvals:
                proposal.status = "approved"
                proposal.updated_at = now

        await self._session.commit()
        await self._session.refresh(approval)
        return self._approval_to_domain(approval)

    async def start_execution(
        self,
        *,
        proposal_id: str,
        idempotency_key: str,
    ) -> AgentActionExecutionResult:
        now = _utcnow()
        proposal = await self._session.scalar(
            select(AgentActionProposalORM)
            .where(AgentActionProposalORM.id == proposal_id)
            .with_for_update()
        )
        if (
            proposal is None
            or proposal.status != "approved"
            or _as_aware(proposal.expires_at) <= now
        ):
            await self._session.rollback()
            raise AgentActionTransitionConflictError()

        policy = AgentApprovalPolicy.model_validate(proposal.approval_policy_json)
        approved_count = int(
            await self._session.scalar(
                select(func.count())
                .select_from(AgentActionApprovalORM)
                .where(
                    AgentActionApprovalORM.proposal_id == proposal_id,
                    AgentActionApprovalORM.decision == "approved",
                    AgentActionApprovalORM.consumed_at.is_(None),
                )
            )
            or 0
        )
        if approved_count < policy.minimum_approvals:
            await self._session.rollback()
            raise AgentActionTransitionConflictError()

        proposal.status = "executing"
        proposal.updated_at = now
        consumed = await self._session.execute(
            update(AgentActionApprovalORM)
            .where(
                AgentActionApprovalORM.proposal_id == proposal_id,
                AgentActionApprovalORM.decision == "approved",
                AgentActionApprovalORM.consumed_at.is_(None),
            )
            .values(consumed_at=now)
        )
        if consumed.rowcount < policy.minimum_approvals:
            await self._session.rollback()
            raise AgentActionTransitionConflictError()

        execution = AgentActionExecutionORM(
            id=uuid.uuid4().hex,
            proposal_id=proposal_id,
            idempotency_key=idempotency_key,
            outcome="executing",
            attempt_count=1,
            last_attempt_at=now,
            reconciliation_status="not_required",
            started_at=now,
        )
        self._session.add(execution)
        try:
            await self._session.commit()
        except IntegrityError as exception:
            await self._session.rollback()
            raise AgentActionTransitionConflictError() from exception
        await self._session.refresh(execution)
        return self._execution_to_domain(execution)

    async def create_rollback_link(
        self,
        *,
        source_proposal_id: str,
        rollback_proposal_id: str,
        created_by_user_id: str,
    ) -> None:
        self._session.add(
            AgentActionRollbackORM(
                id=uuid.uuid4().hex,
                source_proposal_id=source_proposal_id,
                rollback_proposal_id=rollback_proposal_id,
                created_by_user_id=created_by_user_id,
                created_at=_utcnow(),
            )
        )
        try:
            await self._session.commit()
        except IntegrityError as exception:
            await self._session.rollback()
            raise AgentActionTransitionConflictError() from exception
