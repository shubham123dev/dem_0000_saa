from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class ActionCapabilityOut(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    label: str
    description: str
    resource_label: str
    risk_level: Literal["low", "medium", "high"]
    requires_approval: bool
    supports_dry_run: bool
    available: bool


class ActionCapabilityCatalogueOut(BaseModel):
    model_config = ConfigDict(frozen=True)
    action_capabilities: tuple[ActionCapabilityOut, ...]
    lifecycle: tuple[str, ...] = ("inspect", "propose", "approve_or_reject", "execute", "verify", "reconcile_or_rollback")


class ActionControlChangeOut(BaseModel):
    model_config = ConfigDict(frozen=True)
    field: str
    before: str
    after: str


class ActionApprovalProgressOut(BaseModel):
    model_config = ConfigDict(frozen=True)
    approved: int
    required: int
    complete: bool


class ActionAllowedOperationsOut(BaseModel):
    model_config = ConfigDict(frozen=True)
    approve: bool
    reject: bool
    cancel: bool
    execute: bool
    reconcile: bool
    create_rollback: bool


class ActionExecutionReceiptOut(BaseModel):
    model_config = ConfigDict(frozen=True)
    outcome: Literal["executing", "succeeded", "failed", "reconciliation_required"]
    resource_label: str
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    error_code: str | None
    started_at: datetime
    completed_at: datetime | None
    executed_by: str
    rollback_available: bool

    @field_validator("started_at", "completed_at")
    @classmethod
    def normalize_times(cls, value: datetime | None) -> datetime | None:
        return _utc(value)


class ActionProposalControlOut(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    action_name: str
    action_label: str
    resource_label: str
    status: str
    risk_level: Literal["low", "medium", "high"]
    requested_by: str
    created_at: datetime
    expires_at: datetime
    approval_progress: ActionApprovalProgressOut
    self_approval_allowed: bool
    required_approver_permission: str
    changes: tuple[ActionControlChangeOut, ...]
    allowed_operations: ActionAllowedOperationsOut
    source_conversation_id: str | None
    execution: ActionExecutionReceiptOut | None

    @field_validator("created_at", "expires_at")
    @classmethod
    def normalize_times(cls, value: datetime) -> datetime:
        return _utc(value)  # type: ignore[return-value]


class ActionProposalControlListOut(BaseModel):
    model_config = ConfigDict(frozen=True)
    proposals: tuple[ActionProposalControlOut, ...]
    next_cursor: str | None


class ActionDecisionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str | None = Field(default=None, max_length=1000)
    confirmation: str | None = Field(default=None, max_length=80)

    @field_validator("reason", "confirmation")
    @classmethod
    def normalize_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class ActionExecuteBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    idempotency_key: str = Field(min_length=8, max_length=100)
    confirmation: str | None = Field(default=None, max_length=80)

    @field_validator("idempotency_key", "confirmation")
    @classmethod
    def normalize(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value must contain non-whitespace characters")
        return normalized


class ActionExecutionEventOut(BaseModel):
    model_config = ConfigDict(frozen=True)
    schema_version: Literal[1] = 1
    proposal_id: str
    sequence: int
    type: str
    stage: str
    message: str
    payload: dict[str, Any] | None
    terminal: bool
    occurred_at: datetime

    @field_validator("occurred_at")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        return _utc(value)  # type: ignore[return-value]
