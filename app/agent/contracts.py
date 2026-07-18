from __future__ import annotations

from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.agent.action_contracts import AgentActionDefinition, AgentActionProposalInput


class AgentToolDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    required_argument_names: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentToolCall(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_name: str
    arguments: dict[str, str] = Field(default_factory=dict)


class AgentPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    intent: Literal["read", "action_proposal", "clarification_required"] = "read"
    tool_calls: tuple[AgentToolCall, ...] = Field(default_factory=tuple, max_length=5)
    action_proposal: AgentActionProposalInput | None = None
    clarification_question: str | None = None
    missing_fields: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_exclusive_intent(self) -> AgentPlan:
        if self.intent == "read":
            if (
                not self.tool_calls
                or self.action_proposal is not None
                or self.clarification_question is not None
                or self.missing_fields
            ):
                raise ValueError(
                    "Read plans require tool calls and forbid actions or clarification"
                )
        elif self.intent == "action_proposal":
            if (
                self.tool_calls
                or self.action_proposal is None
                or self.clarification_question is not None
                or self.missing_fields
            ):
                raise ValueError(
                    "Action proposal plans require one proposal and forbid reads or clarification"
                )
        else:
            question = (self.clarification_question or "").strip()
            fields = tuple(item.strip() for item in self.missing_fields if item.strip())
            if (
                self.tool_calls
                or self.action_proposal is not None
                or not question
                or not fields
                or len(fields) != len(set(fields))
            ):
                raise ValueError(
                    "Clarification plans require one question and unique missing fields"
                )
            object.__setattr__(self, "clarification_question", question)
            object.__setattr__(self, "missing_fields", fields)
        return self


class AgentToolResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_name: str
    data: Any


class AgentExecutionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    results: tuple[AgentToolResult, ...]


class AgentModelGateway(Protocol):
    async def create_plan(
        self,
        *,
        user_request: str,
        available_tools: tuple[AgentToolDefinition, ...],
        available_actions: tuple[AgentActionDefinition, ...],
    ) -> AgentPlan:
        ...
