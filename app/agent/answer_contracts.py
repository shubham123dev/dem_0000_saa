from __future__ import annotations

from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.agent.contracts import AgentToolResult


class AgentEvidenceItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    tool_name: str
    data: Any


class AgentAnswerDraft(BaseModel):
    model_config = ConfigDict(frozen=True)

    answer: str = Field(min_length=1, max_length=8000)
    evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=5)


class AgentSynthesisResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    answer: str
    evidence_ids: tuple[str, ...]
    answer_source: Literal["model", "deterministic"]


class AgentCompletedExecution(BaseModel):
    model_config = ConfigDict(frozen=True)

    results: tuple[AgentToolResult, ...]
    evidence: tuple[AgentEvidenceItem, ...]
    synthesis: AgentSynthesisResult


class AgentAnswerGateway(Protocol):
    async def create_answer(
        self,
        *,
        user_request: str,
        evidence: tuple[AgentEvidenceItem, ...],
    ) -> AgentAnswerDraft:
        ...
