from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import ValidationError

from app.agent.action_contracts import AgentActionDefinition, AgentActionProposalInput
from app.agent.contracts import AgentPlan, AgentToolCall, AgentToolDefinition
from app.agent.errors import AgentModelResponseInvalidError
from app.agent.providers.openai_responses import (
    OpenAIResponsesAgentModelGateway as BaseGateway,
