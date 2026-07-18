from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Protocol

from app.agent.answer_contracts import AgentQueryCompletion

AgentRunStatus = Literal[
    "queued",
    "running",
    "cancel_requested",
    "succeeded",
    "clarification_required",
    "proposal_ready",
    "failed",
    "cancelled",
]
AgentRunStage = Literal[
    "request_acceptance",
    "access_check",
    "request_planning",
    "data_retrieval",
    "proposal_preparation",
    "answer_preparation",
    "external_wait",
    "verification",
    "completion",
]
AgentRunEventType = Literal[
    "run.accepted",
    "run.started",
    "activity.updated",
    "clarification.required",
    "proposal.created",
    "answer.completed",
    "run.cancel_requested",
    "run.cancelled",
    "run.failed",
]
TERMINAL_RUN_STATUSES = frozenset(
    {"succeeded", "clarification_required", "proposal_ready", "failed", "cancelled"}
)


class AgentRunCancelled(RuntimeError):
    """Raised internally after a cooperative cancellation checkpoint."""


class AgentRunActivitySink(Protocol):
    async def emit(self, *, stage: AgentRunStage, message: str) -> None: ...
    async def checkpoint(self) -> None: ...


class NullAgentRunActivitySink:
    async def emit(self, *, stage: AgentRunStage, message: str) -> None:
        del stage, message

    async def checkpoint(self) -> None:
        return None


@dataclass(frozen=True)
class AgentConversationRecord:
    id: str
    organization_id: str
    created_by_user_id: str
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class AgentMessageRecord:
    id: str
    conversation_id: str
    run_id: str | None
    sequence: int
    role: str
    content: str
    mode: str | None
    answer_source: str | None
    safe_metadata: dict[str, Any] | None
    created_at: datetime


@dataclass(frozen=True)
class AgentRunRecord:
    id: str
    conversation_id: str
    organization_id: str
    requested_by_user_id: str
    user_message_id: str
    client_request_id: str
    status: AgentRunStatus
    current_stage: str
    final_mode: str | None
    final_message_id: str | None
    proposal_id: str | None
    error_code: str | None
    cancellation_requested_at: datetime | None
    attempt_count: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    @property
    def terminal(self) -> bool:
        return self.status in TERMINAL_RUN_STATUSES


@dataclass(frozen=True)
class AgentRunEventRecord:
    id: str
    run_id: str
    sequence: int
    event_type: AgentRunEventType
    stage: str
    safe_message: str
    safe_payload: dict[str, Any] | None
    terminal: bool
    created_at: datetime


@dataclass(frozen=True)
class CreatedAgentRun:
    conversation: AgentConversationRecord
    run: AgentRunRecord
    user_message: AgentMessageRecord
    created: bool


def safe_activity_for_tool(tool_name: str) -> str:
    if "audit" in tool_name:
        return "Reading recent audit activity"
    if "report" in tool_name:
        return "Reading report access information"
    if any(token in tool_name for token in ("user", "membership", "seat")):
        return "Reading membership and access information"
    if "nucleus" in tool_name:
        return "Reading organization administration information"
    if "workplace" in tool_name or "resource" in tool_name:
        return "Reading the relevant workspace resources"
    return "Reading the relevant workspace information"


def terminal_event_type(completion: AgentQueryCompletion) -> AgentRunEventType:
    if completion.mode == "clarification_required":
        return "clarification.required"
    if completion.mode == "action_proposal":
        return "proposal.created"
    return "answer.completed"
