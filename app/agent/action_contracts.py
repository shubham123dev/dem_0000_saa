from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.models import OrganizationOverview, OrganizationProfile


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
    allow_suspended_organization: bool = False
    model_selectable: bool = True


class AgentActionProposalInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    action_name: str
    arguments: dict[str, str] = Field(default_factory=dict)


class AgentActionChange(BaseModel):
    model_config = ConfigDict(frozen=True)

    field: str
    before: Any
    after: Any


class AgentActionResourcePrecondition(BaseModel):
    """One immutable resource version reviewed by an approver."""

    model_config = ConfigDict(frozen=True)

    resource_type: str = Field(min_length=1, max_length=120)
    resource_id: str = Field(min_length=1, max_length=250)
    observed_version: int = Field(ge=0)


def _canonical_resource_preconditions(
    *,
    resource_type: str,
    resource_id: str,
    observed_resource_version: int,
    resource_preconditions: tuple[AgentActionResourcePrecondition, ...],
) -> tuple[AgentActionResourcePrecondition, ...]:
    primary = AgentActionResourcePrecondition(
        resource_type=resource_type,
        resource_id=resource_id,
        observed_version=observed_resource_version,
    )
    by_key: dict[tuple[str, str], AgentActionResourcePrecondition] = {}
    for item in resource_preconditions:
        key = (item.resource_type, item.resource_id)
        previous = by_key.get(key)
        if previous is not None and previous.observed_version != item.observed_version:
            raise ValueError("Conflicting action resource preconditions")
        by_key[key] = item

    primary_key = (primary.resource_type, primary.resource_id)
    previous_primary = by_key.get(primary_key)
    if (
        previous_primary is not None
        and previous_primary.observed_version != primary.observed_version
    ):
        raise ValueError("Primary resource precondition does not match proposal")
    by_key[primary_key] = primary
    return tuple(
        sorted(
            by_key.values(),
            key=lambda item: (item.resource_type, item.resource_id),
        )
    )


class AgentActionPreparation(BaseModel):
    model_config = ConfigDict(frozen=True)

    normalized_arguments: dict[str, str]
    changes: tuple[AgentActionChange, ...]
    observed_resource_version: int
    resource_type: str
    resource_id: str
    resource_preconditions: tuple[AgentActionResourcePrecondition, ...] = ()
    risk_level: Literal["low", "medium", "high"] | None = None
    approval_policy: AgentApprovalPolicy | None = None
    risk_snapshot: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def normalize_resource_preconditions(self) -> "AgentActionPreparation":
        normalized = _canonical_resource_preconditions(
            resource_type=self.resource_type,
            resource_id=self.resource_id,
            observed_resource_version=self.observed_resource_version,
            resource_preconditions=self.resource_preconditions,
        )
        if normalized != self.resource_preconditions:
            object.__setattr__(self, "resource_preconditions", normalized)
        return self


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
    fingerprint_version: int = Field(default=2, ge=2, le=4)
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
    resource_preconditions: tuple[AgentActionResourcePrecondition, ...] = ()
    approval_policy: AgentApprovalPolicy
    expires_at: datetime
    cancelled_at: datetime | None = None
    stale_at: datetime | None = None
    created_at: datetime

    @model_validator(mode="after")
    def normalize_resource_preconditions(self) -> "AgentActionProposal":
        normalized = _canonical_resource_preconditions(
            resource_type=self.resource_type,
            resource_id=self.resource_id,
            observed_resource_version=self.observed_resource_version,
            resource_preconditions=self.resource_preconditions,
        )
        if normalized != self.resource_preconditions:
            object.__setattr__(self, "resource_preconditions", normalized)
        return self


class AgentActionApproval(BaseModel):
    model_config = ConfigDict(frozen=True)

    proposal_id: str
    decision: Literal["approved", "rejected"]
    decided_by_user_id: str
    decision_reason: str | None
    decided_at: datetime
    consumed_at: datetime | None


class AgentActionExecutionContext(BaseModel):
    """Backend-derived identity and time for one execution attempt."""

    model_config = ConfigDict(frozen=True)

    organization_id: str
    executed_by_user_id: str
    nucleus_actor_id: int | None = None
    execution_started_at: datetime
class AgentActionExecutionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    proposal_id: str
    idempotency_key: str
    executed_by_user_id: str
    nucleus_actor_id: int | None = None
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

    async def get_overview(self, organization_id: str) -> OrganizationOverview:
        ...

    async def update_contact_email_if_version(
        self,
        organization_id: str,
        contact_email: str | None,
        expected_version: int,
    ) -> OrganizationProfile | None:
        ...

    async def update_display_name_if_version(
        self,
        organization_id: str,
        display_name: str,
        expected_version: int,
    ) -> OrganizationProfile | None:
        ...

    async def update_organization_type_if_version(
        self,
        organization_id: str,
        organization_type: str,
        expected_version: int,
    ) -> OrganizationOverview | None:
        ...
