from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import ValidationError

from app.agent.action_contracts import AgentActionDefinition, AgentActionProposalInput
from app.agent.contracts import AgentPlan, AgentToolCall, AgentToolDefinition
from app.agent.errors import AgentModelResponseInvalidError
from app.agent.providers.openai_responses import (
    OpenAIResponsesAgentModelGateway as BaseGateway,
)

logger = logging.getLogger("app.agent_model")
_READ = "read__"
_ACTION = "action__"
_CLARIFY = "clarify__request"


class OpenAIResponsesAgentModelGateway(BaseGateway):
    """Plan with strict registry-derived function calls and fail closed."""

    def _build_plan_request_payload(
        self,
        *,
        user_request: str,
        available_tools: tuple[AgentToolDefinition, ...],
        available_actions: tuple[AgentActionDefinition, ...],
    ) -> dict[str, Any]:
        functions = [
            self._function(
                f"{_READ}{item.name}",
                f"READ ONLY. {item.description}",
                item.required_argument_names,
            )
            for item in available_tools
        ]
        functions += [
            self._function(
                f"{_ACTION}{item.name}",
                "DRY-RUN PROPOSAL ONLY. " + item.description,
                item.required_argument_names,
            )
            for item in available_actions
        ]
        functions.append(
            {
                "type": "function",
                "name": _CLARIFY,
                "description": "Ask for required business values that are missing or ambiguous.",
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
                    "content": [{
                        "type": "input_text",
                        "text": (
                            "Choose exactly one path. For reads, call one to five read__ functions only. "
                            "For a change, call exactly one action__ function only. For missing or ambiguous "
                            "required values, call clarify__request only. Prefer action__invite_organization_user "
                            "when the user says invite; use action__onboard_organization_user only when activation, "
                            "onboarding, or seat assignment is explicitly requested. Never supply organization or "
                            "actor identity, permissions, approvals, proposal IDs, execution commands, credentials, "
                            "or idempotency keys. Action calls create reviewable proposals and never execute changes."
                        ),
                    }],
                },
                {"role": "user", "content": [{"type": "input_text", "text": user_request}]},
            ],
        }

    def _parse_plan(
        self,
        response_payload: dict[str, Any],
        *,
        available_tools: tuple[AgentToolDefinition, ...],
        available_actions: tuple[AgentActionDefinition, ...],
    ) -> AgentPlan:
        try:
            calls = self._calls(response_payload)
            tools = {item.name: item for item in available_tools}
            actions = {item.name: item for item in available_actions}
            reads: list[AgentToolCall] = []
            proposals: list[AgentActionProposalInput] = []
            clarifications: list[tuple[str, tuple[str, ...]]] = []
            for name, arguments in calls:
                if name.startswith(_READ):
                    operation = name[len(_READ):]
                    definition = tools.get(operation)
                    if definition is None:
                        self._reject("unknown_read", response_payload, calls)
                    reads.append(AgentToolCall(
                        tool_name=operation,
                        arguments=self._select_required_arguments(
                            arguments, set(definition.required_argument_names)
                        ),
                    ))
                elif name.startswith(_ACTION):
                    operation = name[len(_ACTION):]
                    definition = actions.get(operation)
                    if definition is None:
                        self._reject("unknown_action", response_payload, calls)
                    proposals.append(AgentActionProposalInput(
                        action_name=operation,
                        arguments=self._select_required_arguments(
                            arguments, set(definition.required_argument_names)
                        ),
                    ))
                elif name == _CLARIFY:
                    if set(arguments) != {"question", "missing_fields"}:
                        self._reject("invalid_clarification", response_payload, calls)
                    question = arguments.get("question")
                    fields = arguments.get("missing_fields")
                    if not isinstance(question, str) or not question.strip():
                        self._reject("invalid_clarification", response_payload, calls)
                    if not isinstance(fields, list) or not fields or not all(
                        isinstance(item, str) and item.strip() for item in fields
                    ):
                        self._reject("invalid_clarification", response_payload, calls)
                    normalized = tuple(item.strip() for item in fields)
                    if len(normalized) != len(set(normalized)):
                        self._reject("duplicate_missing_fields", response_payload, calls)
                    clarifications.append((question.strip(), normalized))
                else:
                    self._reject("unknown_function", response_payload, calls)
            if clarifications:
                if len(calls) != 1:
                    self._reject("mixed_clarification", response_payload, calls)
                question, fields = clarifications[0]
                return AgentPlan(
                    intent="clarification_required",
                    clarification_question=question,
                    missing_fields=fields,
                )
            if proposals:
                if len(calls) != 1:
                    self._reject("mixed_or_multiple_actions", response_payload, calls)
                return AgentPlan(intent="action_proposal", action_proposal=proposals[0])
            if not reads or len(reads) > 5 or len(reads) != len(calls):
                self._reject("invalid_read_plan", response_payload, calls)
            return AgentPlan(intent="read", tool_calls=tuple(reads))
        except AgentModelResponseInvalidError:
            raise
        except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
            self._log_rejection("invalid_function_payload", response_payload, ())
            raise AgentModelResponseInvalidError() from exc

    @staticmethod
    def _function(name: str, description: str, arguments: tuple[str, ...]) -> dict[str, Any]:
        return {
            "type": "function",
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "required": list(arguments),
                "properties": {item: {"type": "string"} for item in arguments},
            },
            "strict": True,
        }

    def _calls(self, payload: dict[str, Any]) -> tuple[tuple[str, dict[str, Any]], ...]:
        output = payload.get("output")
        if not isinstance(output, list):
            self._reject("missing_output", payload, ())
        calls: list[tuple[str, dict[str, Any]]] = []
        for item in output:
            if not isinstance(item, dict) or item.get("type") != "function_call":
                continue
            if item.get("status") not in {None, "completed"}:
                self._reject("incomplete_call", payload, calls)
            name, raw = item.get("name"), item.get("arguments")
            if not isinstance(name, str) or not isinstance(raw, str):
                self._reject("invalid_call_shape", payload, calls)
            arguments = json.loads(raw)
            if not isinstance(arguments, dict):
                self._reject("invalid_arguments", payload, calls)
            calls.append((name, arguments))
        if not calls or len(calls) > 5:
            self._reject("invalid_call_count", payload, calls)
        return tuple(calls)

    def _reject(self, reason: str, payload: dict[str, Any], calls: Any) -> None:
        self._log_rejection(reason, payload, calls)
        raise AgentModelResponseInvalidError()

    def _log_rejection(self, reason: str, payload: dict[str, Any], calls: Any) -> None:
        logger.info(
            "Rejected invalid workplace planner output",
            extra={
                "planner_validation_reason": reason,
                "provider_response_id": payload.get("id"),
                "model": self._model,
                "function_names": [name for name, _ in calls],
            },
        )
