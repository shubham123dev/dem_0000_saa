from __future__ import annotations

from datetime import datetime, timezone
import uuid

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.action_contracts import (
    AgentActionApproval,
    AgentActionChange,
    AgentActionExecutionResult,
    AgentActionProposal,
    AgentActionResourcePrecondition,
    AgentApprovalPolicy,
)
from app.agent.action_state import require_transition
from app.db.action_models import (
    AgentActionApprovalORM,
    AgentActionExecutionORM,
    AgentActionProposalORM,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AgentActionTransitionConflictError(RuntimeError):
    pass


class AgentActionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_proposal(
        self,
        *,
        organization_id: str,
        requested_by_user_id: str,
        action_name: str,
        arguments: dict[str, str],
        changes: tuple[AgentActionChange, ...],
        action_fingerprint: str,
        risk_level: str,
        resource_type: str,
        resource_id: str,
        observed_resource_version: int,
        resource_preconditions: tuple[AgentActionResourcePrecondition, ...],
        fingerprint_version: int,
        approval_policy: AgentApprovalPolicy,
        expires_at: datetime,
    ) -> AgentActionProposal:
        row = AgentActionProposalORM(
            id=uuid.uuid4().hex,
            organization_id=organization_id,
            requested_by_user_id=requested_by_user_id,
            action_name=action_name,
            arguments_json=arguments,
            changes_json=[change.model_dump(mode="json") for change in changes],
            action_fingerprint=action_fingerprint,
            risk_level=risk_level,
            resource_type=resource_type,
            resource_id=resource_id,
            status="pending_approval",
            observed_resource_version=observed_resource_version,
            resource_preconditions_json=[
                item.model_dump(mode="json") for item in resource_preconditions
            ],
            fingerprint_version=fingerprint_version,
            approval_policy_json=approval_policy.model_dump(mode="json"),
            expires_at=expires_at,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return self._proposal_to_domain(row)

    async def get_proposal(
        self,
        *,
        proposal_id: str,
        organization_id: str,
    ) -> AgentActionProposal | None:
        statement = select(AgentActionProposalORM).where(
            AgentActionProposalORM.id == proposal_id,
            AgentActionProposalORM.organization_id == organization_id,
        )
        result = await self._session.execute(statement)
        row = result.scalar_one_or_none()
        return self._proposal_to_domain(row) if row is not None else None

    async def list_proposals(
        self,
        *,
        organization_id: str,
        status: str | None = None,
    ) -> tuple[AgentActionProposal, ...]:
        statement = select(AgentActionProposalORM).where(
            AgentActionProposalORM.organization_id == organization_id
        )
        if status is not None:
            statement = statement.where(AgentActionProposalORM.status == status)
        statement = statement.order_by(
            AgentActionProposalORM.created_at.desc(),
            AgentActionProposalORM.id.desc(),
        )
        result = await self._session.execute(statement)
        return tuple(self._proposal_to_domain(row) for row in result.scalars().all())

    async def get_approval(self, proposal_id: str) -> AgentActionApproval | None:
        statement = select(AgentActionApprovalORM).where(
            AgentActionApprovalORM.proposal_id == proposal_id
        )
        result = await self._session.execute(statement)
        row = result.scalar_one_or_none()
        return self._approval_to_domain(row) if row is not None else None

    async def get_execution(
        self,
        proposal_id: str,
    ) -> AgentActionExecutionResult | None:
        statement = select(AgentActionExecutionORM).where(
            AgentActionExecutionORM.proposal_id == proposal_id
        )
        result = await self._session.execute(statement)
        row = result.scalar_one_or_none()
        return self._execution_to_domain(row) if row is not None else None

    async def decide(
        self,
        *,
        proposal_id: str,
        decided_by_user_id: str,
        decision: str,
        decision_reason: str | None,
    ) -> AgentActionApproval:
        require_transition("pending_approval", decision)
        now = _utcnow()
        proposal_update = (
            update(AgentActionProposalORM)
            .where(
                AgentActionProposalORM.id == proposal_id,
                AgentActionProposalORM.status == "pending_approval",
                AgentActionProposalORM.expires_at > now,
            )
            .values(status=decision, updated_at=now)
        )
        result = await self._session.execute(proposal_update)
        if result.rowcount != 1:
            await self._session.rollback()
            raise AgentActionTransitionConflictError()
        approval_row = AgentActionApprovalORM(
            id=uuid.uuid4().hex,
            proposal_id=proposal_id,
            decision=decision,
            decided_by_user_id=decided_by_user_id,
            decision_reason=decision_reason,
            decided_at=now,
        )
        self._session.add(approval_row)
        try:
            await self._session.commit()
        except IntegrityError as exception:
            await self._session.rollback()
            raise AgentActionTransitionConflictError() from exception
        await self._session.refresh(approval_row)
        return self._approval_to_domain(approval_row)

    async def transition_status(
        self,
        *,
        proposal_id: str,
        current_statuses: tuple[str, ...],
        target_status: str,
    ) -> bool:
        for current_status in current_statuses:
            require_transition(current_status, target_status)
        now = _utcnow()
        values: dict = {"status": target_status, "updated_at": now}
        if target_status == "cancelled":
            values["cancelled_at"] = now
        if target_status == "stale":
            values["stale_at"] = now
        statement = (
            update(AgentActionProposalORM)
            .where(
                AgentActionProposalORM.id == proposal_id,
                AgentActionProposalORM.status.in_(current_statuses),
            )
            .values(**values)
        )
        result = await self._session.execute(statement)
        if result.rowcount != 1:
            await self._session.rollback()
            return False
        await self._session.commit()
        return True

    async def start_execution(
        self,
        *,
        proposal_id: str,
        idempotency_key: str,
    ) -> AgentActionExecutionResult:
        require_transition("approved", "executing")
        now = _utcnow()
        proposal_update = (
            update(AgentActionProposalORM)
            .where(
                AgentActionProposalORM.id == proposal_id,
                AgentActionProposalORM.status == "approved",
                AgentActionProposalORM.expires_at > now,
            )
            .values(status="executing", updated_at=now)
        )
        proposal_result = await self._session.execute(proposal_update)
        if proposal_result.rowcount != 1:
            await self._session.rollback()
            raise AgentActionTransitionConflictError()
        approval_update = (
            update(AgentActionApprovalORM)
            .where(
                AgentActionApprovalORM.proposal_id == proposal_id,
                AgentActionApprovalORM.decision == "approved",
                AgentActionApprovalORM.consumed_at.is_(None),
            )
            .values(consumed_at=now)
        )
        approval_result = await self._session.execute(approval_update)
        if approval_result.rowcount != 1:
            await self._session.rollback()
            raise AgentActionTransitionConflictError()
        execution_row = AgentActionExecutionORM(
            id=uuid.uuid4().hex,
            proposal_id=proposal_id,
            idempotency_key=idempotency_key,
            outcome="executing",
            attempt_count=1,
            last_attempt_at=now,
            reconciliation_status="not_required",
            started_at=now,
        )
        self._session.add(execution_row)
        try:
            await self._session.commit()
        except IntegrityError as exception:
            await self._session.rollback()
            raise AgentActionTransitionConflictError() from exception
        await self._session.refresh(execution_row)
        return self._execution_to_domain(execution_row)

    async def complete_execution(
        self,
        *,
        proposal_id: str,
        outcome: str,
        result: dict | None,
        error_code: str | None,
        provider_operation_id: str | None = None,
        reconciliation_status: str | None = None,
        audit_pending: bool = False,
    ) -> AgentActionExecutionResult:
        current_statuses = (
            ("executing", "reconciliation_required")
            if outcome in {"succeeded", "failed"}
            else ("executing",)
        )
        for current_status in current_statuses:
            require_transition(current_status, outcome)
        now = _utcnow()
        execution_update = (
            update(AgentActionExecutionORM)
            .where(
                AgentActionExecutionORM.proposal_id == proposal_id,
                AgentActionExecutionORM.outcome.in_(current_statuses),
            )
            .values(
                outcome=outcome,
                result_json=result,
                error_code=error_code,
                provider_operation_id=provider_operation_id,
                reconciliation_status=reconciliation_status,
                audit_pending=audit_pending,
                completed_at=now if outcome in {"succeeded", "failed"} else None,
                last_attempt_at=now,
            )
        )
        execution_result = await self._session.execute(execution_update)
        if execution_result.rowcount != 1:
            await self._session.rollback()
            raise AgentActionTransitionConflictError()
        proposal_update = (
            update(AgentActionProposalORM)
            .where(
                AgentActionProposalORM.id == proposal_id,
                AgentActionProposalORM.status.in_(current_statuses),
            )
            .values(status=outcome, updated_at=now)
        )
        proposal_result = await self._session.execute(proposal_update)
        if proposal_result.rowcount != 1:
            await self._session.rollback()
            raise AgentActionTransitionConflictError()
        await self._session.commit()
        execution = await self.get_execution(proposal_id)
        if execution is None:
            raise AgentActionTransitionConflictError()
        return execution

    async def mark_stale_execution(self, proposal_id: str) -> AgentActionExecutionResult:
        require_transition("executing", "stale")
        now = _utcnow()
        execution_update = (
            update(AgentActionExecutionORM)
            .where(
                AgentActionExecutionORM.proposal_id == proposal_id,
                AgentActionExecutionORM.outcome == "executing",
            )
            .values(
                outcome="failed",
                error_code="agent_action_stale",
                reconciliation_status="not_required",
                completed_at=now,
                last_attempt_at=now,
            )
        )
        execution_result = await self._session.execute(execution_update)
        proposal_update = (
            update(AgentActionProposalORM)
            .where(
                AgentActionProposalORM.id == proposal_id,
                AgentActionProposalORM.status == "executing",
            )
            .values(status="stale", stale_at=now, updated_at=now)
        )
        proposal_result = await self._session.execute(proposal_update)
        if execution_result.rowcount != 1 or proposal_result.rowcount != 1:
            await self._session.rollback()
            raise AgentActionTransitionConflictError()
        await self._session.commit()
        execution = await self.get_execution(proposal_id)
        if execution is None:
            raise AgentActionTransitionConflictError()
        return execution

    async def keep_reconciliation_required(
        self,
        *,
        proposal_id: str,
        audit_pending: bool,
    ) -> AgentActionExecutionResult:
        now = _utcnow()
        statement = (
            update(AgentActionExecutionORM)
            .where(
                AgentActionExecutionORM.proposal_id == proposal_id,
                AgentActionExecutionORM.outcome == "reconciliation_required",
            )
            .values(
                error_code="action_outcome_unknown",
                reconciliation_status="required",
                audit_pending=audit_pending,
                last_attempt_at=now,
            )
        )
        result = await self._session.execute(statement)
        if result.rowcount != 1:
            await self._session.rollback()
            raise AgentActionTransitionConflictError()
        await self._session.commit()
        execution = await self.get_execution(proposal_id)
        if execution is None:
            raise AgentActionTransitionConflictError()
        return execution

    async def mark_audit_pending(self, proposal_id: str, pending: bool) -> None:
        statement = (
            update(AgentActionExecutionORM)
            .where(AgentActionExecutionORM.proposal_id == proposal_id)
            .values(audit_pending=pending)
        )
        await self._session.execute(statement)
        await self._session.commit()

    async def increment_reconciliation_attempt(self, proposal_id: str) -> None:
        execution = await self.get_execution(proposal_id)
        if execution is None:
            raise AgentActionTransitionConflictError()
        statement = (
            update(AgentActionExecutionORM)
            .where(AgentActionExecutionORM.proposal_id == proposal_id)
            .values(
                attempt_count=execution.attempt_count + 1,
                last_attempt_at=_utcnow(),
                reconciliation_status="checking",
            )
        )
        await self._session.execute(statement)
        await self._session.commit()

    @staticmethod
    def _proposal_to_domain(row: AgentActionProposalORM) -> AgentActionProposal:
        policy_payload = dict(row.approval_policy_json or {})
        if not policy_payload:
            policy_payload = {
                "self_approval_allowed": True,
                "required_approver_permission": "organization.profile.update",
                "minimum_approvals": 1,
            }
        return AgentActionProposal(
            id=row.id,
            organization_id=row.organization_id,
            requested_by_user_id=row.requested_by_user_id,
            action_name=row.action_name,
            arguments=dict(row.arguments_json),
            changes=tuple(
                AgentActionChange.model_validate(item) for item in row.changes_json
            ),
            action_fingerprint=row.action_fingerprint,
            fingerprint_version=row.fingerprint_version,
            risk_level=row.risk_level,
            resource_type=row.resource_type,
            resource_id=row.resource_id,
            status=row.status,
            observed_resource_version=row.observed_resource_version,
            resource_preconditions=tuple(
                AgentActionResourcePrecondition.model_validate(item)
                for item in (row.resource_preconditions_json or [])
            ),
            approval_policy=AgentApprovalPolicy.model_validate(policy_payload),
            expires_at=row.expires_at,
            cancelled_at=row.cancelled_at,
            stale_at=row.stale_at,
            created_at=row.created_at,
        )

    @staticmethod
    def _approval_to_domain(row: AgentActionApprovalORM) -> AgentActionApproval:
        return AgentActionApproval(
            proposal_id=row.proposal_id,
            decision=row.decision,
            decided_by_user_id=row.decided_by_user_id,
            decision_reason=row.decision_reason,
            decided_at=row.decided_at,
            consumed_at=row.consumed_at,
        )

    @staticmethod
    def _execution_to_domain(row: AgentActionExecutionORM) -> AgentActionExecutionResult:
        return AgentActionExecutionResult(
            proposal_id=row.proposal_id,
            idempotency_key=row.idempotency_key,
            outcome=row.outcome,
            result=row.result_json,
            error_code=row.error_code,
            attempt_count=row.attempt_count,
            last_attempt_at=row.last_attempt_at,
            provider_operation_id=row.provider_operation_id,
            reconciliation_status=row.reconciliation_status,
            audit_pending=row.audit_pending,
            started_at=row.started_at,
            completed_at=row.completed_at,
        )
