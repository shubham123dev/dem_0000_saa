from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


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

    tool_calls: tuple[AgentToolCall, ...] = Field(min_length=1, max_length=5)


class AgentModelGateway(Protocol):
    async def create_plan(
        self,
        *,
        user_request: str,
        available_tools: tuple[AgentToolDefinition, ...],
    ) -> AgentPlan:
        ...
