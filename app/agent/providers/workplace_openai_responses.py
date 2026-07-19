from __future__ import annotations

import copy
import json
from typing import Any

from app.agent.action_contracts import AgentActionDefinition
from app.agent.contracts import AgentPlan, AgentToolDefinition
from app.agent.providers.openai_responses import (
    OpenAIResponsesAgentModelGateway as BaseOpenAIResponsesAgentModelGateway,
)


class OpenAIResponsesAgentModelGateway(BaseOpenAIResponsesAgentModelGateway):
    """Normalize harmless read-plan follow-up text before strict validation.

    Structured output can return an optional preference question alongside