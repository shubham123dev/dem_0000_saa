from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.agent.action_contracts import AgentActionProposal


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


class AgentQueryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    mode: Literal["read", "action_proposal"] = "read"
    organization_id: str
    answer: str
    evidence_ids: tuple[str, ...] = ()
    answer_source: Literal["model", "deterministic"]
    results: tuple[AgentToolResultOut, ...] = ()
    action_proposal: AgentActionProposal | None = None

    @model_validator(mode="after")
    def validate_mode_payload(self) -> AgentQueryResponse:
        if self.mode == "read":
            if self.action_proposal is not None:
                raise ValueError("Read responses cannot include action proposals")
        elif self.action_proposal is None or self.results or self.evidence_ids:
            raise ValueError(
                "Action proposal responses require a proposal and no read evidence"
            )
        return self
