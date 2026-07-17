from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.agent.action_contracts import (
    AgentActionApproval,
    AgentActionExecutionResult,
    AgentActionProposal,
)


class AgentActionProposalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_name: Literal["update_organization_contact_email"]
    contact_email: str = Field(min_length=3, max_length=320)

    @field_validator("contact_email")
    @classmethod
    def validate_contact_email(cls, value: str) -> str:
        normalized_value = value.strip().lower()
        local_part, separator, domain_part = normalized_value.partition("@")
        if not separator or not local_part or "." not in domain_part:
            raise ValueError("Contact email is invalid")
        return normalized_value


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


class AgentActionApprovalResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    approval: AgentActionApproval


class AgentActionExecutionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    execution: AgentActionExecutionResult
