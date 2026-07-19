from __future__ import annotations

from datetime import datetime, timezone
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.action_control_contracts import AgentActionExecutionEventRecord
from app.db.action_control_models import AgentActionExecutionEventORM
from app.db.action_models import (
    AgentActionApprovalORM,
    AgentActionExecutionORM,
    AgentActionProposalORM,
)
from app.db.agent_run_models import AgentRunORM
from app.db.orm_models import UserORM


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _bounded(value: str, limit: int) -> str:
    compact = " ".join(value.split())
    return compact if len(compact) <= limit else compact[: limit - 1] + "…"


class ActionControlRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append_event(
        self,
        *,
        proposal_id: str,
        event_type: str,
        stage: str,
        message: str,
        payload: dict[str, Any] | None,
        terminal: bool,
        dedupe_key: str,
    ) -> AgentActionExecutionEventRecord:
        existing = await self.get_event_by_dedupe_key(
            proposal_id=proposal_id,
            dedupe_key=dedupe_key,
        )
        if existing is not None:
            return existing
        for _attempt in range(8):
            result = await self._session.execute(
                select(func.max(AgentActionExecutionEventORM.sequence)).where(
                    AgentActionExecutionEventORM.proposal_id == proposal_id
                )
            )
            sequence = int(result.scalar_one_or_none() or 0) + 1
            row = AgentActionExecutionEventORM(
                id=uuid.uuid4().hex,
                proposal_id=proposal_id,
                sequence=sequence,
                dedupe_key=_bounded(dedupe_key, 120),
                event_type=_bounded(event_type, 80),
                stage=_bounded(stage, 80),
                safe_message=_bounded(message, 240),
                safe_payload_json=payload,
                terminal=terminal,
            )
            self._session.add(row)
            try:
                await self._session.commit()
                await self._session.refresh(row)
                return self._event_record(row)
            except IntegrityError:
                await self._session.rollback()
                existing = await self.get_event_by_dedupe_key(
                    proposal_id=proposal_id,
                    dedupe_key=dedupe_key,
                )
                if existing is not None:
                    return existing
        raise RuntimeError("Could not allocate action execution event sequence")

    async def get_event_by_dedupe_key(
        self,
        *,
        proposal_id: str,
        dedupe_key: str,
    ) -> AgentActionExecutionEventRecord | None:
        result = await self._session.execute(
            select(AgentActionExecutionEventORM).where(
                AgentActionExecutionEventORM.proposal_id == proposal_id,
                AgentActionExecutionEventORM.dedupe_key == dedupe_key,
            )
        )
        row = result.scalar_one_or_none()
        return self._event_record(row) if row is not None else None

    async def list_events(
        self,
        *,
        proposal_id: str,
        after_sequence: int,
        limit: int = 200,
    ) -> tuple[AgentActionExecutionEventRecord, ...]:
        result = await self._session.execute(
            select(AgentActionExecutionEventORM)
            .where(
                AgentActionExecutionEventORM.proposal_id == proposal_id,
                AgentActionExecutionEventORM.sequence > after_sequence,
            )
            .order_by(AgentActionExecutionEventORM.sequence.asc())
            .limit(limit)
        )
        return tuple(self._event_record(row) for row in result.scalars().all())

    async def count_approvals(self, proposal_id: str) -> int:
        result = await self._session.execute(
            select(func.count(AgentActionApprovalORM.id)).where(
                AgentActionApprovalORM.proposal_id == proposal_id,
                AgentActionApprovalORM.decision == "approved",
            )
        )
        return int(result.scalar_one())

    async def proposal_source(self, proposal_id: str) -> tuple[str | None, str | None]:
        result = await self._session.execute(
            select(
                AgentActionProposalORM.source_agent_run_id,
                AgentRunORM.conversation_id,
            )
            .outerjoin(
                AgentRunORM,
                AgentRunORM.id == AgentActionProposalORM.source_agent_run_id,
            )
            .where(AgentActionProposalORM.id == proposal_id)
        )
        row = result.one_or_none()
        if row is None:
            return None, None
        return row[0], row[1]

    async def user_label(self, user_id: str) -> str:
        result = await self._session.execute(
            select(UserORM.display_name).where(UserORM.id == user_id)
        )
        value = result.scalar_one_or_none()
        return value or "Workspace user"

    async def execution_row(self, proposal_id: str) -> AgentActionExecutionORM | None:
        result = await self._session.execute(
            select(AgentActionExecutionORM).where(
                AgentActionExecutionORM.proposal_id == proposal_id
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _event_record(row: AgentActionExecutionEventORM) -> AgentActionExecutionEventRecord:
        return AgentActionExecutionEventRecord(
            id=row.id,
            proposal_id=row.proposal_id,
            sequence=row.sequence,
            event_type=row.event_type,
            stage=row.stage,
            safe_message=row.safe_message,
            safe_payload=row.safe_payload_json,
            terminal=row.terminal,
            created_at=_aware(row.created_at),
        )
