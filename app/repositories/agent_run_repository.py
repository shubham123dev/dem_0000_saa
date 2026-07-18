from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid
from typing import Any

from sqlalchemy import and_, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.answer_contracts import AgentQueryCompletion
from app.agent.run_contracts import (
    AgentConversationRecord,
    AgentMessageRecord,
    AgentRunEventRecord,
    AgentRunRecord,
    CreatedAgentRun,
    TERMINAL_RUN_STATUSES,
    terminal_event_type,
)
from app.db.agent_run_models import (
    AgentConversationORM,
    AgentMessageORM,
    AgentRunEventORM,
    AgentRunORM,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)


def _bounded_text(value: str, limit: int) -> str:
    compact = value.strip()
    return compact if len(compact) <= limit else compact[: limit - 1] + "…"


def _proposal_metadata(completion: AgentQueryCompletion) -> dict[str, Any] | None:
    proposal = completion.action_proposal
    if proposal is None:
        return None
    return {
        "action_name": proposal.action_name,
        "risk_level": proposal.risk_level,
        "status": proposal.status,
        "changes": [change.model_dump(mode="json") for change in proposal.changes[:8]],
        "expires_at": proposal.expires_at.isoformat(),
    }


class AgentConversationBusyRepositoryError(RuntimeError):
    pass


def _completion_metadata(completion: AgentQueryCompletion) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "source_count": max(len(completion.evidence_ids), len(completion.results)),
        "missing_fields": [
            _bounded_text(field, 160) for field in completion.missing_fields[:20]
        ],
    }
    proposal = _proposal_metadata(completion)
    if proposal is not None:
        metadata["action_proposal"] = proposal
    return metadata


class AgentRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_run(
        self,
        *,
        organization_id: str,
        requested_by_user_id: str,
        query: str,
        client_request_id: str,
        conversation_id: str | None,
        request_id: str | None,
    ) -> CreatedAgentRun:
        existing = await self.get_by_client_request_id(
            organization_id=organization_id,
            requested_by_user_id=requested_by_user_id,
            client_request_id=client_request_id,
        )
        if existing is not None:
            conversation = await self.require_conversation(
                conversation_id=existing.conversation_id,
                organization_id=organization_id,
                user_id=requested_by_user_id,
            )
            message = await self.require_message(existing.user_message_id)
            return CreatedAgentRun(conversation, existing, message, False)

        for _attempt in range(20):
            existing = await self.get_by_client_request_id(
                organization_id=organization_id,
                requested_by_user_id=requested_by_user_id,
                client_request_id=client_request_id,
            )
            if existing is not None:
                conversation = await self.require_conversation(
                    conversation_id=existing.conversation_id,
                    organization_id=organization_id,
                    user_id=requested_by_user_id,
                )
                message = await self.require_message(existing.user_message_id)
                return CreatedAgentRun(conversation, existing, message, False)
            now = _utcnow()
            try:
                if conversation_id is None:
                    conversation_row = AgentConversationORM(
                        id=uuid.uuid4().hex,
                        organization_id=organization_id,
                        created_by_user_id=requested_by_user_id,
                        status="active",
                        next_message_sequence=2,
                        version=1,
                        created_at=now,
                        updated_at=now,
                    )
                    self._session.add(conversation_row)
                    message_sequence = 1
                else:
                    conversation_row = await self._conversation_row(
                        conversation_id=conversation_id,
                        organization_id=organization_id,
                        user_id=requested_by_user_id,
                    )
                    if await self.find_active_run(conversation_id=conversation_row.id):
                        raise AgentConversationBusyRepositoryError()
                    message_sequence = conversation_row.next_message_sequence
                    result = await self._session.execute(
                        update(AgentConversationORM)
                        .where(
                            AgentConversationORM.id == conversation_row.id,
                            AgentConversationORM.version == conversation_row.version,
                        )
                        .values(
                            next_message_sequence=message_sequence + 1,
                            version=conversation_row.version + 1,
                            updated_at=now,
                        )
                    )
                    if result.rowcount != 1:
                        await self._session.rollback()
                        continue

                run_id = uuid.uuid4().hex
                message_id = uuid.uuid4().hex
                message_row = AgentMessageORM(
                    id=message_id,
                    conversation_id=conversation_row.id,
                    run_id=run_id,
                    sequence=message_sequence,
                    role="user",
                    content=query,
                    mode=None,
                    answer_source=None,
                    safe_metadata_json=None,
                    created_at=now,
                )
                run_row = AgentRunORM(
                    id=run_id,
                    conversation_id=conversation_row.id,
                    organization_id=organization_id,
                    requested_by_user_id=requested_by_user_id,
                    user_message_id=message_id,
                    client_request_id=client_request_id,
                    request_id=request_id,
                    active_slot=1,
                    status="queued",
                    current_stage="request_acceptance",
                    attempt_count=0,
                    next_event_sequence=2,
                    version=1,
                    created_at=now,
                )
                event_row = AgentRunEventORM(
                    id=uuid.uuid4().hex,
                    run_id=run_id,
                    sequence=1,
                    event_type="run.accepted",
                    stage="request_acceptance",
                    safe_message="Request accepted",
                    safe_payload_json=None,
                    terminal=False,
                    created_at=now,
                )
                self._session.add(conversation_row)
                self._session.add(run_row)
                await self._session.flush()
                self._session.add_all((message_row, event_row))
                await self._session.commit()
                return CreatedAgentRun(
                    self._conversation_to_record(conversation_row),
                    self._run_to_record(run_row),
                    self._message_to_record(message_row),
                    True,
                )
            except IntegrityError:
                await self._session.rollback()
                self._session.expunge_all()
                existing = await self.get_by_client_request_id(
                    organization_id=organization_id,
                    requested_by_user_id=requested_by_user_id,
                    client_request_id=client_request_id,
                )
                if existing is not None:
                    conversation = await self.require_conversation(
                        conversation_id=existing.conversation_id,
                        organization_id=organization_id,
                        user_id=requested_by_user_id,
                    )
                    message = await self.require_message(existing.user_message_id)
                    return CreatedAgentRun(conversation, existing, message, False)
                if conversation_id is not None:
                    active = await self.find_active_run(
                        conversation_id=conversation_id
                    )
                    if active is not None:
                        raise AgentConversationBusyRepositoryError()
        raise RuntimeError("Could not allocate a conversation message sequence")

    async def get_by_client_request_id(
        self,
        *,
        organization_id: str,
        requested_by_user_id: str,
        client_request_id: str,
    ) -> AgentRunRecord | None:
        result = await self._session.execute(
            select(AgentRunORM).where(
                AgentRunORM.organization_id == organization_id,
                AgentRunORM.requested_by_user_id == requested_by_user_id,
                AgentRunORM.client_request_id == client_request_id,
            )
        )
        row = result.scalar_one_or_none()
        return self._run_to_record(row) if row is not None else None

    async def require_conversation(
        self, *, conversation_id: str, organization_id: str, user_id: str
    ) -> AgentConversationRecord:
        return self._conversation_to_record(
            await self._conversation_row(
                conversation_id=conversation_id,
                organization_id=organization_id,
                user_id=user_id,
            )
        )

    async def _conversation_row(
        self, *, conversation_id: str, organization_id: str, user_id: str
    ) -> AgentConversationORM:
        result = await self._session.execute(
            select(AgentConversationORM).where(
                AgentConversationORM.id == conversation_id,
                AgentConversationORM.organization_id == organization_id,
                AgentConversationORM.created_by_user_id == user_id,
                AgentConversationORM.status == "active",
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise LookupError("agent_conversation_not_found")
        return row

    async def require_run(
        self, *, run_id: str, organization_id: str, user_id: str
    ) -> AgentRunRecord:
        result = await self._session.execute(
            select(AgentRunORM).where(
                AgentRunORM.id == run_id,
                AgentRunORM.organization_id == organization_id,
                AgentRunORM.requested_by_user_id == user_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise LookupError("agent_run_not_found")
        return self._run_to_record(row)

    async def get_run_internal(self, run_id: str) -> AgentRunRecord | None:
        row = await self._session.get(AgentRunORM, run_id)
        return self._run_to_record(row) if row is not None else None

    async def require_message(self, message_id: str) -> AgentMessageRecord:
        row = await self._session.get(AgentMessageORM, message_id)
        if row is None:
            raise LookupError("agent_message_not_found")
        return self._message_to_record(row)

    async def list_messages(
        self, *, conversation_id: str, limit: int = 100
    ) -> tuple[AgentMessageRecord, ...]:
        result = await self._session.execute(
            select(AgentMessageORM)
            .where(AgentMessageORM.conversation_id == conversation_id)
            .order_by(AgentMessageORM.sequence.asc())
            .limit(limit)
        )
        return tuple(self._message_to_record(row) for row in result.scalars().all())

    async def conversation_context(
        self, *, conversation_id: str, through_message_id: str
    ) -> str:
        messages = await self.list_messages(conversation_id=conversation_id, limit=40)
        selected: list[AgentMessageRecord] = []
        for message in messages:
            selected.append(message)
            if message.id == through_message_id:
                break
        if len(selected) == 1:
            return selected[0].content
        lines = ["Conversation context:"]
        for message in selected[-12:]:
            label = "User" if message.role == "user" else "Assistant"
            lines.append(f"{label}: {_bounded_text(message.content, 1600)}")
        lines.append(
            "Respond to the latest user message using the earlier messages only as context."
        )
        context = "\n\n".join(lines)
        return context[-12000:]

    async def find_active_run(
        self, *, conversation_id: str
    ) -> AgentRunRecord | None:
        result = await self._session.execute(
            select(AgentRunORM)
            .where(
                AgentRunORM.conversation_id == conversation_id,
                AgentRunORM.status.in_(
                    ("queued", "running", "cancel_requested")
                ),
            )
            .order_by(AgentRunORM.created_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return self._run_to_record(row) if row is not None else None

    async def request_cancellation(self, run_id: str) -> AgentRunRecord:
        for _attempt in range(6):
            row = await self._session.get(AgentRunORM, run_id)
            if row is None:
                raise LookupError("agent_run_not_found")
            if row.status in TERMINAL_RUN_STATUSES:
                return self._run_to_record(row)
            if row.cancellation_requested_at is not None:
                return self._run_to_record(row)
            now = _utcnow()
            result = await self._session.execute(
                update(AgentRunORM)
                .where(
                    AgentRunORM.id == run_id,
                    AgentRunORM.version == row.version,
                    AgentRunORM.status.in_(
                        ("queued", "running", "cancel_requested")
                    ),
                )
                .values(
                    cancellation_requested_at=now,
                    status="cancel_requested",
                    version=row.version + 1,
                )
            )
            if result.rowcount != 1:
                await self._session.rollback()
                self._session.expire_all()
                continue
            await self._session.commit()
            await self.append_event(
                run_id=run_id,
                event_type="run.cancel_requested",
                stage=row.current_stage,
                message="Cancellation requested",
                payload=None,
                terminal=False,
            )
            refreshed = await self.get_run_internal(run_id)
            if refreshed is None:
                raise LookupError("agent_run_not_found")
            return refreshed
        raise RuntimeError("Could not request agent run cancellation")

    async def claim_next(
        self, *, worker_id: str, lease_seconds: int = 45
    ) -> AgentRunRecord | None:
        now = _utcnow()
        result = await self._session.execute(
            select(AgentRunORM)
            .where(
                or_(
                    AgentRunORM.status == "queued",
                    and_(
                        AgentRunORM.status == "cancel_requested",
                        or_(
                            AgentRunORM.lease_owner.is_(None),
                            AgentRunORM.lease_expires_at.is_(None),
                            AgentRunORM.lease_expires_at < now,
                        ),
                    ),
                    and_(
                        AgentRunORM.status == "running",
                        AgentRunORM.lease_expires_at.is_not(None),
                        AgentRunORM.lease_expires_at < now,
                    ),
                )
            )
            .order_by(AgentRunORM.created_at.asc())
            .limit(8)
        )
        for candidate in result.scalars().all():
            claimed = await self._session.execute(
                update(AgentRunORM)
                .where(
                    AgentRunORM.id == candidate.id,
                    AgentRunORM.version == candidate.version,
                )
                .values(
                    status="running",
                    lease_owner=worker_id,
                    lease_expires_at=now + timedelta(seconds=lease_seconds),
                    started_at=candidate.started_at or now,
                    attempt_count=candidate.attempt_count + 1,
                    version=candidate.version + 1,
                )
            )
            if claimed.rowcount == 1:
                await self._session.commit()
                row = await self._session.get(AgentRunORM, candidate.id)
                if row is None:
                    return None
                if candidate.attempt_count == 0:
                    await self.append_event(
                        run_id=row.id,
                        event_type="run.started",
                        stage="request_acceptance",
                        message="Work started",
                        payload=None,
                        terminal=False,
                    )
                return self._run_to_record(row)
            await self._session.rollback()
        return None

    async def renew_lease(
        self, *, run_id: str, worker_id: str, lease_seconds: int = 45
    ) -> bool:
        now = _utcnow()
        result = await self._session.execute(
            update(AgentRunORM)
            .where(
                AgentRunORM.id == run_id,
                AgentRunORM.lease_owner == worker_id,
                AgentRunORM.status.in_(("running", "cancel_requested")),
            )
            .values(lease_expires_at=now + timedelta(seconds=lease_seconds))
        )
        await self._session.commit()
        return result.rowcount == 1

    async def is_cancellation_requested(self, run_id: str) -> bool:
        result = await self._session.execute(
            select(AgentRunORM.cancellation_requested_at).where(
                AgentRunORM.id == run_id
            )
        )
        return result.scalar_one_or_none() is not None

    async def append_event(
        self,
        *,
        run_id: str,
        event_type: str,
        stage: str,
        message: str,
        payload: dict[str, Any] | None,
        terminal: bool,
    ) -> AgentRunEventRecord:
        for _attempt in range(6):
            row = await self._session.get(AgentRunORM, run_id)
            if row is None:
                raise LookupError("agent_run_not_found")
            sequence = row.next_event_sequence
            now = _utcnow()
            changed = await self._session.execute(
                update(AgentRunORM)
                .where(
                    AgentRunORM.id == run_id,
                    AgentRunORM.version == row.version,
                )
                .values(
                    next_event_sequence=sequence + 1,
                    current_stage=stage,
                    version=row.version + 1,
                )
            )
            if changed.rowcount != 1:
                await self._session.rollback()
                self._session.expire_all()
                continue
            event = AgentRunEventORM(
                id=uuid.uuid4().hex,
                run_id=run_id,
                sequence=sequence,
                event_type=event_type,
                stage=stage,
                safe_message=_bounded_text(message, 240),
                safe_payload_json=payload,
                terminal=terminal,
                created_at=now,
            )
            self._session.add(event)
            try:
                await self._session.commit()
                return self._event_to_record(event)
            except IntegrityError:
                await self._session.rollback()
                self._session.expire_all()
        raise RuntimeError("Could not allocate an agent run event sequence")

    async def complete_run(
        self, *, run_id: str, completion: AgentQueryCompletion
    ) -> AgentMessageRecord:
        for _attempt in range(6):
            run = await self._session.get(AgentRunORM, run_id)
            if run is None:
                raise LookupError("agent_run_not_found")
            conversation = await self._session.get(
                AgentConversationORM, run.conversation_id
            )
            if conversation is None:
                raise LookupError("agent_conversation_not_found")
            now = _utcnow()
            message_sequence = conversation.next_message_sequence
            event_sequence = run.next_event_sequence
            conversation_update = await self._session.execute(
                update(AgentConversationORM)
                .where(
                    AgentConversationORM.id == conversation.id,
                    AgentConversationORM.version == conversation.version,
                )
                .values(
                    next_message_sequence=message_sequence + 1,
                    version=conversation.version + 1,
                    updated_at=now,
                )
            )
            run_status = {
                "read": "succeeded",
                "clarification_required": "clarification_required",
                "action_proposal": "proposal_ready",
            }[completion.mode]
            message_id = uuid.uuid4().hex
            run_update = await self._session.execute(
                update(AgentRunORM)
                .where(
                    AgentRunORM.id == run_id,
                    AgentRunORM.version == run.version,
                    AgentRunORM.status.in_(("running", "cancel_requested")),
                )
                .values(
                    status=run_status,
                    active_slot=None,
                    current_stage="completion",
                    final_mode=completion.mode,
                    final_message_id=message_id,
                    proposal_id=(
                        completion.action_proposal.id
                        if completion.action_proposal is not None
                        else None
                    ),
                    completed_at=now,
                    lease_owner=None,
                    lease_expires_at=None,
                    next_event_sequence=event_sequence + 1,
                    version=run.version + 1,
                )
            )
            if conversation_update.rowcount != 1 or run_update.rowcount != 1:
                await self._session.rollback()
                self._session.expire_all()
                continue
            metadata = _completion_metadata(completion)
            message = AgentMessageORM(
                id=message_id,
                conversation_id=conversation.id,
                run_id=run_id,
                sequence=message_sequence,
                role="assistant",
                content=_bounded_text(completion.answer, 8000),
                mode=completion.mode,
                answer_source=completion.answer_source,
                safe_metadata_json=metadata,
                created_at=now,
            )
            public_message = self._message_public_dict(message, metadata)
            event = AgentRunEventORM(
                id=uuid.uuid4().hex,
                run_id=run_id,
                sequence=event_sequence,
                event_type=terminal_event_type(completion),
                stage="completion",
                safe_message={
                    "read": "Answer ready",
                    "clarification_required": "More information is needed",
                    "action_proposal": "Reviewable proposal ready",
                }[completion.mode],
                safe_payload_json={"message": public_message},
                terminal=True,
                created_at=now,
            )
            self._session.add_all((message, event))
            try:
                await self._session.commit()
                return self._message_to_record(message)
            except IntegrityError:
                await self._session.rollback()
                self._session.expire_all()
        raise RuntimeError("Could not complete the agent run atomically")

    async def cancel_run(self, run_id: str) -> None:
        await self._finish_without_message(
            run_id=run_id,
            status="cancelled",
            error_code=None,
            event_type="run.cancelled",
            message="Run cancelled",
        )

    async def fail_run(self, run_id: str, error_code: str) -> None:
        await self._finish_without_message(
            run_id=run_id,
            status="failed",
            error_code=error_code,
            event_type="run.failed",
            message="The run could not be completed",
        )

    async def _finish_without_message(
        self,
        *,
        run_id: str,
        status: str,
        error_code: str | None,
        event_type: str,
        message: str,
    ) -> None:
        for _attempt in range(6):
            run = await self._session.get(AgentRunORM, run_id)
            if run is None:
                raise LookupError("agent_run_not_found")
            if run.status in TERMINAL_RUN_STATUSES:
                return
            now = _utcnow()
            sequence = run.next_event_sequence
            result = await self._session.execute(
                update(AgentRunORM)
                .where(
                    AgentRunORM.id == run_id,
                    AgentRunORM.version == run.version,
                )
                .values(
                    status=status,
                    active_slot=None,
                    current_stage="completion",
                    error_code=error_code,
                    completed_at=now,
                    lease_owner=None,
                    lease_expires_at=None,
                    next_event_sequence=sequence + 1,
                    version=run.version + 1,
                )
            )
            if result.rowcount != 1:
                await self._session.rollback()
                self._session.expire_all()
                continue
            self._session.add(
                AgentRunEventORM(
                    id=uuid.uuid4().hex,
                    run_id=run_id,
                    sequence=sequence,
                    event_type=event_type,
                    stage="completion",
                    safe_message=message,
                    safe_payload_json={"error_code": error_code}
                    if error_code
                    else None,
                    terminal=True,
                    created_at=now,
                )
            )
            await self._session.commit()
            return
        raise RuntimeError("Could not finish the agent run")

    async def list_events(
        self, *, run_id: str, after_sequence: int, limit: int = 200
    ) -> tuple[AgentRunEventRecord, ...]:
        result = await self._session.execute(
            select(AgentRunEventORM)
            .where(
                AgentRunEventORM.run_id == run_id,
                AgentRunEventORM.sequence > after_sequence,
            )
            .order_by(AgentRunEventORM.sequence.asc())
            .limit(limit)
        )
        return tuple(self._event_to_record(row) for row in result.scalars().all())

    @staticmethod
    def _conversation_to_record(row: AgentConversationORM) -> AgentConversationRecord:
        return AgentConversationRecord(
            id=row.id,
            organization_id=row.organization_id,
            created_by_user_id=row.created_by_user_id,
            status=row.status,
            created_at=_aware(row.created_at),
            updated_at=_aware(row.updated_at),
        )

    @staticmethod
    def _message_to_record(row: AgentMessageORM) -> AgentMessageRecord:
        return AgentMessageRecord(
            id=row.id,
            conversation_id=row.conversation_id,
            run_id=row.run_id,
            sequence=row.sequence,
            role=row.role,
            content=row.content,
            mode=row.mode,
            answer_source=row.answer_source,
            safe_metadata=row.safe_metadata_json,
            created_at=_aware(row.created_at),
        )

    @staticmethod
    def _run_to_record(row: AgentRunORM) -> AgentRunRecord:
        return AgentRunRecord(
            id=row.id,
            conversation_id=row.conversation_id,
            organization_id=row.organization_id,
            requested_by_user_id=row.requested_by_user_id,
            user_message_id=row.user_message_id,
            client_request_id=row.client_request_id,
            status=row.status,
            current_stage=row.current_stage,
            final_mode=row.final_mode,
            final_message_id=row.final_message_id,
            proposal_id=row.proposal_id,
            error_code=row.error_code,
            cancellation_requested_at=_aware(row.cancellation_requested_at),
            attempt_count=row.attempt_count,
            created_at=_aware(row.created_at),
            started_at=_aware(row.started_at),
            completed_at=_aware(row.completed_at),
        )

    @staticmethod
    def _event_to_record(row: AgentRunEventORM) -> AgentRunEventRecord:
        return AgentRunEventRecord(
            id=row.id,
            run_id=row.run_id,
            sequence=row.sequence,
            event_type=row.event_type,
            stage=row.stage,
            safe_message=row.safe_message,
            safe_payload=row.safe_payload_json,
            terminal=row.terminal,
            created_at=_aware(row.created_at),
        )

    @staticmethod
    def _message_public_dict(
        row: AgentMessageORM, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return {
            "id": row.id,
            "sequence": row.sequence,
            "role": row.role,
            "content": row.content,
            "mode": row.mode,
            "answer_source": row.answer_source,
            "safe_metadata": metadata if metadata is not None else row.safe_metadata_json,
            "created_at": row.created_at.isoformat(),
        }
