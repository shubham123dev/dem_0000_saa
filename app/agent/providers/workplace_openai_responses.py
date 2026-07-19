from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import ValidationError

from app.agent.action_contracts import AgentActionDefinition, AgentActionProposalInput
from app.agent.contracts import AgentPlan, AgentToolCall, AgentToolDefinition
from app.agent.errors import AgentModelResponseInvalidError
from app.agent.providers.openai_responses import (
    OpenAIResponsesAgentModelGateway as BaseOpenAIResponsesAgentModelGateway,
)

logger = logging.getLogger("app.agent_model")

_READ_PREFIX = "read__"
_ACTION_PREFIX = "action__"
_CLARIFICATION_FUNCTION = "clarify__request"
_MAX_READ_CALLS = 5


class OpenAIResponsesAgentModelGateway(BaseOpenAIResponsesAgentModelGateway):
    """Use strict function calls for workplace planning.

    Each registered read tool and model-selectable action receives its own exact
    argument schema. The model must choose one exclusive planning path: one to five
    reads, exactly one dry-run action proposal, or one clarification request. The
    backend parser and registries remain authoritative and fail closed.
    """

    def _build_plan_request_payload(
        self,
        *,
        user_request: str,
        available_tools: tuple[AgentToolDefinition, ...],
        available_actions: tuple[AgentActionDefinition, ...],
    ) -> dict[str, Any]:
        functions = [
            self._planning_function(
                name=f"{_READ_PREFIX}{definition.name}",
                description=(
                    f"READ ONLY. {definition.description} Use only when the user "
                    "is asking to inspect information, not change it."
                ),
                required_argument_names=definition.required_argument_names,
            )
            for definition in available_tools
        ]
        functions.extend(
            self._planning_function(
                name=f"{_ACTION_PREFIX}{definition.name}",
                description=(
                    f"DRY-RUN ACTION PROPOSAL ONLY. {definition.description} "
                    "Calling this function never executes the change; backend "
                    "authorization, review and explicit approval remain required."
                ),
                required_argument_names=definition.required_argument_names,
            )
            for definition in available_actions
        )
        functions.append(
            {
                "type": "function",
                "name": _CLARIFICATION_FUNCTION,
                "description": (
                    "Ask one concise clarification question only when a required "
                    "business value or identifier is missing or ambiguous. Never "
                    "guess identifiers, roles, values or approval decisions."
                ),
                "parameters": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["question", "missing_fields"],
                    "properties": {
                        "question": {"type": "string"},
                        "missing_fields": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
                "strict": True,
            }
        )
        return {
            "model": self._model,
            "store": False,
            "max_output_tokens": self._maximum_output_tokens,
            "parallel_tool_calls": True,
            "tool_choice": "required",
            "tools": functions,
            "input": [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Choose exactly one exclusive