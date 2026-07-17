from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AgentActionDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    required_argument_names: tuple[str, ...]
    required_permission: str
    resource_type: str
    risk_level: Literal["low", "medium", "high"]
    requires_approval: bool
    supports_dry_run: bool


class AgentActionProposalInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    action_name: str
    arguments: dict[str, str] = Field(default_factory=dict)


class AgentActionChange(BaseModel):
    model_config = ConfigDict(frozen=True)

    field: str
    before: Any
    after: Any


class AgentActionProposal(Base