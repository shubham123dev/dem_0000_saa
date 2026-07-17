from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json

from app.agent.action_contracts import (
    AgentActionChange,
    AgentActionDefinition,
    AgentActionProposalInput,
    AgentApprovalPolicy,
)
from app.domain.enums import Permission


class InvalidAgentActionProposalError(ValueError):
    pass


class AgentActionRegistry:
    def __init__(self) -> None:
        self._definitions = {
           