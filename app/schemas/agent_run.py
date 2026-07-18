from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AgentRunCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=4000)
    client_request_id: str = Field(min_length=8, max_length=64)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=64)

    @field_validator("query", "client_request_id")
    @classmethod
    def strip_non_empty(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value must contain non-whitespace characters")
        return normalized


class AgentRunMessageOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    sequence: int
    role: Literal["user", "assistant"]
    content: str
    mode: Literal["read", "action_proposal", "clarification_required"] | None
    answer_source: Literal["model", "deterministic"] | None
    safe_metadata: dict[str, Any] | None
    created_at: datetime


class AgentRunOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    conversation_id: str
    status: Literal[
        "queued",
        "running",
        "cancel_requested",
        "succeeded",
        "clarification_required",
        "proposal_ready",
        "failed",
        "cancelled",
    ]
    current_stage: str
    final_mode: str | None
    error_code: str | None
    cancellation_requested_at: datetime | None
    attempt_count: int
    terminal: bool
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class AgentRunCreateResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    conversation_id: str
    run: AgentRunOut
    user_message: AgentRunMessageOut
    events_url: str
    created: bool


class AgentConversationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    conversation_id: str
    messages: tuple[AgentRunMessageOut, ...]
    active_run: AgentRunOut | None


class AgentRunEventOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: Literal[1] = 1
    run_id: str
    sequence: int
    type: str
    stage: str
    message: str
    payload: dict[str, Any] | None
    terminal: bool
    occurred_at: datetime
