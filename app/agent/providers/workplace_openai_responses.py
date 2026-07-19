from __future__ import annotations

import json
import logging
from typing import Any

from app.agent.action_contracts import AgentActionDefinition, AgentActionProposalInput
from app.agent.action_selection import scope_actions
from app.agent.contracts import AgentPlan, AgentToolCall, AgentToolDefinition
from app.agent.errors import AgentModelResponseInvalidError
from app.agent.providers.openai_responses import OpenAIResponsesAgentModelGateway as BaseGateway

logger = logging.getLogger("app.agent_model")
_READ, _ACTION, _CLARIFY = "read__", "action__", "clarify__request"


class OpenAIResponsesAgentModelGateway(BaseGateway):
    """Strict function-call planner with registry-derived action precedence."""

    def _action_scope(
        self,
        request: str,
        actions: tuple[AgentActionDefinition, ...],
    ) -> tuple[AgentActionDefinition, ...]:
        return scope_actions(request, actions)

    def _build_plan_request_payload(
        self,
        *,
        user_request: str,
        available_tools: tuple[AgentToolDefinition, ...],
        available_actions: tuple[AgentActionDefinition, ...],
    ) -> dict[str, Any]:
        scoped_actions = self._action_scope(user_request, available_actions)
        actions = scoped_actions or available_actions
        functions = [] if scoped_actions else [
            self._function(
                _READ + item.name,
                "READ ONLY. " + item.description,
                item.required_argument_names,
            )
            for item in available_tools
        ]
        functions += [
            self._function(
                _ACTION + item.name,
                "DRY-RUN PROPOSAL ONLY. " + item.description,
                item.required_argument_names,
            )
            for item in actions
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
        instruction = (
            "Choose one path: one to five read__ calls, exactly one action__ call, "
            "or clarify__request. Actions only prepare reviewable proposals."
        )
        if scoped_actions:
            instruction = (
                "The latest user message is an explicit change command. Choose exactly "
                "one offered action__ function, or clarify__request if required values "
                "are missing. Use earlier conversation messages only as context. Do not "
                "answer with a read."
            )
        return {
            "model": self._model,
            "store": False,
            "max_output_tokens": self._maximum_output_tokens,
            "parallel_tool_calls": not bool(scoped_actions),
            "tool_choice": "required",
            "tools": functions,
            "input": [
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": instruction}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": user_request}],
                },
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
                    operation = name[len(_READ) :]
                    definition = tools.get(operation)
                    if definition is None:
                        self._reject("unknown_read", response_payload, calls)
                    reads.append(
                        AgentToolCall(
                            tool_name=operation,
                            arguments=self._select_required_arguments(
                                arguments,
                                set(definition.required_argument_names),
                            ),
                        )
                    )
                elif name.startswith(_ACTION):
                    operation = name[len(_ACTION) :]
                    definition = actions.get(operation)
                    if definition is None:
                        self._reject("unknown_action", response_payload, calls)
                    proposals.append(
                        AgentActionProposalInput(
                            action_name=operation,
                            arguments=self._select_required_arguments(
                                arguments,
                                set(definition.required_argument_names),
                            ),
                        )
                    )
                elif name == _CLARIFY:
                    question = arguments.get("question")
                    fields = arguments.get("missing_fields")
                    if (
                        set(arguments) != {"question", "missing_fields"}
                        or not isinstance(question, str)
                        or not question.strip()
                        or not isinstance(fields, list)
                        or not fields
                        or not all(
                            isinstance(item, str) and item.strip() for item in fields
                        )
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
        except (json.JSONDecodeError, TypeError, ValueError) as exception:
            raise AgentModelResponseInvalidError() from exception

    @staticmethod
    def _function(
        name: str,
        description: str,
        arguments: tuple[str, ...],
    ) -> dict[str, Any]:
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

    def _calls(
        self,
        payload: dict[str, Any],
    ) -> tuple[tuple[str, dict[str, Any]], ...]:
        output = payload.get("output")
        if not isinstance(output, list):
            self._reject("missing_output", payload, ())
        calls: list[tuple[str, dict[str, Any]]] = []
        for item in output:
            if isinstance(item, dict) and item.get("type") == "function_call":
                name = item.get("name")
                raw_arguments = item.get("arguments")
                if not isinstance(name, str) or not isinstance(raw_arguments, str):
                    self._reject("invalid_call_shape", payload, calls)
                arguments = json.loads(raw_arguments)
                if not isinstance(arguments, dict):
                    self._reject("invalid_arguments", payload, calls)
                calls.append((name, arguments))
        if not calls or len(calls) > 5:
            self._reject("invalid_call_count", payload, calls)
        return tuple(calls)

    def _reject(self, reason: str, payload: dict[str, Any], calls: Any) -> None:
        logger.info(
            "Rejected invalid workplace planner output",
            extra={
                "planner_validation_reason": reason,
                "provider_response_id": payload.get("id"),
                "model": self._model,
                "function_names": [name for name, _ in calls],
            },
        )
        raise AgentModelResponseInvalidError()
