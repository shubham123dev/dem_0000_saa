from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models import OrganizationProfile


class AgentApprovalPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    self_approval_allowed: bool = True
    required_approver_permission: str
    minimum_approvals: int = Field(default=1, ge=1, le=10)


class AgentActionDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    required_argument_names: tuple[str, ...]
    required_permission: str
    resource_type: str
    risk_level: Literal["low", "medium", "high"]
    requires_approval: bool
    supports_dry_run: bool
    approval_policy: AgentApprovalPolicy


class AgentActionProposalInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    action_name: str
    arguments: dict[str, str] = Field(default_factory=dict)


class AgentActionChange(BaseModel):
    model_config = ConfigDict(frozen=True)

    field: str
    before: Any
    after: Any


class AgentActionPreparation(BaseModel):
    model_config = ConfigDict(frozen=True)

    normalized_arguments: dict[str, str]
    changes: tuple[AgentActionChange, ...]
    observed_resource_version: int
    resource_type: str
    resource_id: str


class AgentActionHandlerResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    resource_type: str
    resource_id: str
    before: dict[str, Any]
    after: dict[str, Any]
    external_operation_id: str | None = None


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
        "cancelled",
        "stale",
        "executing",
        "succeeded",
        "failed",
        "reconciliation_required",
    ]
    changes: tuple[AgentActionChange, ...]
    observed_resource_version: int
    approval_policy: AgentApprovalPolicy
    expires_at: datetime
    cancelled_at: datetime | None = None
    stale_at: datetime | None = None
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
    outcome: Literal[
        "executing",
        "succeeded",
        "failed",
        "reconciliation_required",
    ]
    result: dict[str, Any] | None
    error_code: str | None
    attempt_count: int = 1
    last_attempt_at: datetime | None = None
    provider_operation_id: str | None = None
    reconciliation_status: str | None = None
    audit_pending: bool = False
    started_at: datetime
    completed_at: datetime | None


class AgentActionHandler(Protocol):
    async def prepare(
        self,
        *,
        organization_id: str,
        arguments: dict[str, str],
    ) -> AgentActionPreparation:
        ...

    async def execute(
        self,
        *,
        proposal: AgentActionProposal,
    ) -> AgentActionHandlerResult:
        ...

    async def reconcile(
        self,
        *,
        proposal: AgentActionProposal,
        execution: AgentActionExecutionResult,
    ) -> AgentActionHandlerResult | None:
        ...


class VersionedOrganizationMutationGateway(Protocol):
    async def get_profile(self, organization_id: str) -> OrganizationProfile:
        ...

    async def update_contact_email_if_version(
        self,
        organization_id: str,
        contact_email: str,
        expected_version: int,
    ) -> OrganizationProfile | None:
        ...
