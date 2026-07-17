from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, or_, select, update

from app.agent.action_contracts import AgentActionExecutionResult, AgentActionProposal
from app.db.action_models import AgentActionExecutionORM, AgentActionProposalORM
from app.repositories.multi_approval_agent_action_repository import (
    MultiApprovalAgentActionRepository,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class HardenedAgentActionRepository(MultiApprovalAgentActionRepository):
    async def count_pending(
        self,
        *,
        organization_id: str,
        requested_by_user_id: str | None = None,
    ) -> int:
        statement = (
            select(func.count())
            .select_from(AgentActionProposalORM)
            .where(
                AgentActionProposalORM.organization_id == organization_id,
                AgentActionProposalORM.status.in_(("pending_approval", "approved")),
            )
        )
        if requested_by_user_id is not None:
            statement = statement.where(
                AgentActionProposalORM.requested_by_user_id == requested_by_user_id
            )
        return int(await self._session.scalar(statement) or 0)

    async def count_recent_proposals(
        self,
        *,
        organization_id: str,
        requested_by_user_id: str,
        since: datetime,
    ) -> int:
        statement = (
            select(func.count())
            .select_from(AgentActionProposalORM)
            .where(
                AgentActionProposalORM.organization_id == organization_id,
                AgentActionProposalORM.requested_by_user_id == requested_by_user_id,
                AgentActionProposalORM.created_at >= since,
            )
        )
        return int(await self._session.scalar(statement) or 0)

    async def list_proposals_page(
        self,
        *,
        organization_id: str,
        status: str | None,
        action_name: str | None,
        requested_by_user_id: str | None,
        limit: int,
        cursor: str | None,
    ) -> tuple[tuple[AgentActionProposal, ...], str | None]:
        statement = select(AgentActionProposalORM).where(
            AgentActionProposalORM.organization_id == organization_id
        )
        if status is not None:
            statement = statement.where(AgentActionProposalORM.status == status)
        if action_name is not None:
            statement = statement.where(AgentActionProposalORM.action_name == action_name)
        if requested_by_user_id is not None:
            statement = statement.where(
                AgentActionProposalORM.requested_by_user_id == requested_by_user_id
            )
        if cursor is not None:
            cursor_row = await self._session.get(AgentActionProposalORM, cursor)
            if cursor_row is not None and cursor_row.organization_id == organization_id:
                statement = statement.where(
                    or_(
                        AgentActionProposalORM.created_at < cursor_row.created_at,
                        (
                            AgentActionProposalORM.created_at == cursor_row.created_at
                        )
                        & (AgentActionProposalORM.id < cursor_row.id),
                    )
                )
        statement = statement.order_by(
            AgentActionProposalORM.created_at.desc(),
            AgentActionProposalORM.id.desc(),
        ).limit(limit + 1)
        rows = (await self._session.execute(statement)).scalars().all()
        page_rows = rows[:limit]
        next_cursor = page_rows[-1].id if len(rows) > limit and page_rows else None
        return (
            tuple(self._proposal_to_domain(row) for row in page_rows),
            next_cursor,
        )

    async def list_audit_pending_executions(
        self,
        *,
        limit: int,
        maximum_attempts: int,
    ) -> tuple[AgentActionExecutionResult, ...]:
        rows = (
            await self._session.execute(
                select(AgentActionExecutionORM)
                .where(
                    AgentActionExecutionORM.audit_pending.is_(True),
                    AgentActionExecutionORM.audit_replay_attempts < maximum_attempts,
                )
                .order_by(
                    AgentActionExecutionORM.audit_replay_attempts.asc(),
                    AgentActionExecutionORM.last_attempt_at.asc(),
                )
                .limit(limit)
            )
        ).scalars().all()
        return tuple(self._execution_to_domain(row) for row in rows)

    async def record_audit_replay(
        self,
        *,
        proposal_id: str,
        success: bool,
        error_code: str | None,
    ) -> AgentActionExecutionResult:
        now = _utcnow()
        values = {
            "audit_replay_attempts": AgentActionExecutionORM.audit_replay_attempts + 1,
            "audit_last_attempt_at": now,
            "audit_last_error": error_code,
        }
        if success:
            values["audit_pending"] = False
        await self._session.execute(
            update(AgentActionExecutionORM)
            .where(AgentActionExecutionORM.proposal_id == proposal_id)
            .values(**values)
        )
        await self._session.commit()
        execution = await self.get_execution(proposal_id)
        if execution is None:
            raise RuntimeError("Action execution was not found")
        return execution

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
        current = await self.get_execution(proposal_id)
        preserved_audit_pending = audit_pending or (
            current.audit_pending if current is not None else False
        )
        return await super().complete_execution(
            proposal_id=proposal_id,
            outcome=outcome,
            result=result,
            error_code=error_code,
            provider_operation_id=provider_operation_id,
            reconciliation_status=reconciliation_status,
            audit_pending=preserved_audit_pending,
        )
