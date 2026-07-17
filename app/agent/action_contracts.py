from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AgentActionDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    required_argument_names: tuple[str, ...]
    required_permission: str
    resource_type: str
    risk_level: Literal["low", "medium", "high"]
    requires_approval: bool
    supports_dry_run: bool


class AgentActionProposalInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    action_name: str
    arguments: dict[str, str] = Field(default_factory=dict)


class AgentActionChange(BaseModel):
    model_config = ConfigDict(frozen=True)

    field: str
    before: Any
    after: Any


class AgentActionProposal(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    organization_id: str
    requested_by_user_id: str
    action_name: str
    arguments: dict[str, str]
    action_fingerprint: str
    risk_level: Literal["low", "medium", "high"]
    resource_type: str
    resource_id: str
    status: Literal[
        "pending_approval",
        "approved",
        "rejected",
        "expired",
        "executing",
        "succeeded",
        "failed",
    ]
    changes: tuple[AgentActionChange, ...]
    expires_at: datetime
    created_at: datetime


class AgentActionApproval(BaseModel):
    model_config = ConfigDict(frozen=True)

    proposal_id: str
    decision: Literal["approved", "rejected"]
    decided_by_user_id: str
    decision_reason: str | None
    decided_at: datetime
    consumed_at: datetime | None


class AgentActionExecutionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    proposal_id: str
    idempotency_key: str
    outcome: Literal["executing", "succeeded", "failed"]
    result: dict[str, Any] | None
    error_code: str | None
    started_at: datetime
    completed_at: datetime | None
