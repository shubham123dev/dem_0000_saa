from __future__ import annotations

from datetime import datetime, timezone
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.action_contracts import (
    AgentActionApproval,
    AgentActionChange,
    AgentActionExecutionResult,
    AgentActionProposal,
)
from app.db.action_models import (
    AgentActionApprovalORM,
    AgentActionExecutionORM,
    AgentActionProposalORM,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


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

    async def get_approval(self, proposal_id: str) -> AgentActionApproval | None:
        statement = select(AgentActionApprovalORM).where(
            AgentActionApprovalORM.proposal_id == proposal_id
        )
        result = await self._session.execute(statement)
        row = result.scalar_one_or_none()
        return self._approval_to_domain(row) if row is not None else None

    async def decide(
        self,
        *,
        proposal_id: str,
        decided_by_user_id: str,
        decision: str,
        decision_reason: str | None,
    ) -> AgentActionApproval:
        proposal_row = await self._session.get(AgentActionProposalORM, proposal_id)
        if proposal_row is None:
            raise LookupError("Action proposal not found")
        approval_row = AgentActionApprovalORM(
            id=uuid.uuid4().hex,
            proposal_id=proposal_id,
            decision=decision,
            decided_by_user_id=decided_by_user_id,
            decision_reason=decision_reason,
        )
        proposal_row.status = decision
        self._session.add(approval_row)
        await self._session.commit()
        await self._session.refresh(approval_row)
        return self._approval_to_domain(approval_row)

    async def mark_expired(self, proposal_id: str) -> None:
        proposal_row = await self._session.get(AgentActionProposalORM, proposal_id)
        if proposal_row is not None and proposal_row.status == "pending_approval":
            proposal_row.status = "expired"
            await self._session.commit()

    async def start_execution(
        self,
        *,
        proposal_id: str,
        idempotency_key: str,
    ) -> AgentActionExecutionResult:
        proposal_row = await self._session.get(AgentActionProposalORM, proposal_id)
        if proposal_row is None:
            raise LookupError("Action proposal not found")
        approval_statement = select(AgentActionApprovalORM).where(
            AgentActionApprovalORM.proposal_id == proposal_id
        )
        approval_result = await self._session.execute(approval_statement)
        approval_row = approval_result.scalar_one_or_none()
        if approval_row is None or approval_row.decision != "approved":
            raise PermissionError("Approved action approval is required")
        if approval_row.consumed_at is not None:
            raise RuntimeError("Action approval was already consumed")
        now = _utcnow()
        approval_row.consumed_at = now
        proposal_row.status = "executing"
        execution_row = AgentActionExecutionORM(
            id=uuid.uuid4().hex,
            proposal_id=proposal_id,
            idempotency_key=idempotency_key,
            outcome="failed",
            started_at=now,
        )
        self._session.add(execution_row)
        await self._session.commit()
        await self._session.refresh(execution_row)
        return self._execution_to_domain(execution_row)

    async def complete_execution(
        self,
        *,
        proposal_id: str,
        outcome: str,
        result: dict | None,
        error_code: str | None,
    ) -> AgentActionExecutionResult:
        statement = select(AgentActionExecutionORM).where(
            AgentActionExecutionORM.proposal_id == proposal_id
        )
        execution_result = await self._session.execute(statement)
        execution_row = execution_result.scalar_one()
        proposal_row = await self._session.get(AgentActionProposalORM, proposal_id)
        completed_at = _utcnow()
        execution_row.outcome = outcome
        execution_row.result_json = result
        execution_row.error_code = error_code
        execution_row.completed_at = completed_at
        if proposal_row is not None:
            proposal_row.status = "succeeded" if outcome == "succeeded" else "failed"
        await self._session.commit()
        await self._session.refresh(execution_row)
        return self._execution_to_domain(execution_row)

    @staticmethod
    def _proposal_to_domain(row: AgentActionProposalORM) -> AgentActionProposal:
        return AgentActionProposal(
            id=row.id,
            organization_id=row.organization_id,
            requested_by_user_id=row.requested_by_user_id,
            action_name=row.action_name,
            arguments=dict(row.arguments_json),
            changes=tuple(AgentActionChange.model_validate(item) for item in row.changes_json),
            action_fingerprint=row.action_fingerprint,
            risk_level=row.risk_level,
            resource_type=row.resource_type,
            resource_id=row.resource_id,
            status=row.status,
            expires_at=row.expires_at,
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
            started_at=row.started_at,
            completed_at=row.completed_at,
        )
