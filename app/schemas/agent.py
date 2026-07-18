from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.agent.action_contracts import AgentActionChange


class AgentQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=4000)

    @field_validator("query")
    @classmethod
    def validate_query_content(cls, query: str) -> str:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("Query must contain non-whitespace characters")
        return normalized_query


class AgentToolResultOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_name: str
    data: Any


class AgentActionProposalSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    action_name: str
    risk_level: Literal["low", "medium", "high"]
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


class AgentQueryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    mode: Literal["read", "action_proposal", "clarification_required"] = "read"
    organization_id: str
    answer: str
    evidence_ids: tuple[str, ...] = ()
    answer_source: Literal["model", "deterministic"]
    results: tuple[AgentToolResultOut, ...] = ()
    action_proposal: AgentActionProposalSummary | None = None
    missing_fields: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_mode_payload(self) -> AgentQueryResponse:
        if self.mode == "read":
            if self.action_proposal is not None or self.missing_fields:
                raise ValueError(
                    "Read responses cannot include action proposals or missing fields"
                )
        elif self.mode == "action_proposal":
            if (
                self.action_proposal is None
                or self.results
                or self.evidence_ids
                or self.missing_fields
            ):
                raise ValueError(
                    "Action proposal responses require a proposal and no read evidence"
                )
        elif (
            self.action_proposal is not None
            or self.results
            or self.evidence_ids
            or not self.missing_fields
        ):
            raise ValueError(
                "Clarification responses require missing fields and no execution payload"
            )
        return self
