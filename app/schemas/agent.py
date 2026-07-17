from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


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

    organization_id: str
    answer: str
    evidence_ids: tuple[str, ...]
    answer_source: Literal["model", "deterministic"]
    results: tuple[AgentToolResultOut, ...]
