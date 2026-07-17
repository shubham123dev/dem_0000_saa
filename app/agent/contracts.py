from __future__ import annotations

from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.agent.action_contracts import AgentActionDefinition, AgentActionProposalInput


class AgentToolDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    required_argument_names: tuple[str, ...] = ()


class AgentToolCall(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_name: str
    arguments: dict[str, str] = Field(default_factory=dict)


class AgentPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    intent: Literal["read", "action_proposal"] = "read"
    tool_calls: tuple[AgentToolCall, ...] = Field(default_factory=tuple, max_length=5)
    action_proposal: AgentActionProposalInput | None = None

    @model_validator(mode="after")
    def validate_exclusive_intent(self) -> AgentPlan:
        if self.intent == "read":
            if not self.tool_calls or self.action_proposal is not None:
                raise ValueError("Read plans require tool calls and forbid action proposals")
        elif self.tool_calls or self.action_proposal is None:
            raise ValueError(
                "Action proposal plans require one proposal and forbid read tool calls"
            )
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
