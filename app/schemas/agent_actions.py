from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.agent.action_contracts import (
    AgentActionApproval,
    AgentActionExecutionResult,
    AgentActionProposal,
)

AgentActionStatusFilter = Literal[
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

AgentActionName = Literal[
    "update_organization_contact_email",
    "update_nucleus_organization_account_field",
    "clear_nucleus_organization_account_field",
    "grant_nucleus_category_access",
    "revoke_nucleus_category_access",
    "grant_nucleus_report_access",
    "revoke_nucleus_report_access",
    "update_nucleus_organization_permissions",
    "invite_organization_user",
    "activate_organization_membership",
    "update_organization_member_role",
    "remove_organization_user",
    "assign_organization_seat",
    "revoke_organization_seat",
    "grant_organization_report_access",
    "revoke_organization_report_access",
]


class AgentActionProposalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_name: AgentActionName
    arguments: dict[str, str] = Field(default_factory=dict, max_length=12)
    contact_email: str | None = Field(default=None, min_length=3, max_length=320)

    @field_validator("arguments")
    @classmethod
    def validate_arguments(cls, value: dict[str, str]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for name, argument in value.items():
            normalized_name = name.strip()
            normalized_value = argument.strip()
            if (
                not normalized_name
                or len(normalized_name) > 100
                or not normalized_value
                or len(normalized_value) > 500
            ):
                raise ValueError("Action arguments are invalid")
            normalized[normalized_name] = normalized_value
        return normalized

    @field_validator("contact_email")
    @classmethod
    def validate_contact_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        local, separator, domain = normalized.partition("@")
        if not separator or not local or "." not in domain:
            raise ValueError("Contact email is invalid")
        return normalized

    @model_validator(mode="after")
    def validate_compatible_payload(self) -> "AgentActionProposalRequest":
        if self.contact_email is not None:
            if self.action_name != "update_organization_contact_email" or self.arguments:
                raise ValueError(
                    "contact_email is only valid for the contact-email action"
                )
        elif not self.arguments:
            raise ValueError("Action arguments are required")
        return self

    def resolved_arguments(self) -> dict[str, str]:
        if self.contact_email is not None:
            return {"contact_email": self.contact_email}
        return dict(self.arguments)


class AgentActionDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, max_length=500)


class AgentActionExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    idempotency_key: str = Field(min_length=8, max_length=200)


class AgentActionProposalResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    proposal: AgentActionProposal
    requires_approval: bool = True
    dry_run: bool = True


class AgentActionProposalListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    proposals: tuple[AgentActionProposal, ...]
    next_cursor: str | None = None


class AgentActionApprovalResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    approval: AgentActionApproval


class AgentActionExecutionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    execution: AgentActionExecutionResult
