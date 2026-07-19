from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.agent.action_contracts import AgentActionDefinition, AgentActionProposalInput
from app.agent.contracts import AgentPlan, AgentToolCall, AgentToolDefinition
from app.agent.errors import AgentModelResponseInvalidError
from app.agent.providers.openai_responses import OpenAIResponsesAgentModelGateway as BaseGateway

logger = logging.getLogger("app.agent_model")
_READ, _ACTION, _CLARIFY = "read__", "action__", "clarify__request"
_WORDS = re.compile(r"[a-z0-9]+")
_PREFIX = {"please", "kindly", "can", "could", "would", "will", "you", "i", "want", "need", "to", "just", "me"}
_GENERIC = {"organization", "workplace", "nucleus", "resource", "resources", "account"}
_CONTEXT_PREFIX = "Conversation context:"
_USER_MARKER = "\n\nUser: "
_CONTEXT_TRAILER = "\n\nRespond to the latest user message"


def _words(value: str) -> tuple[str, ...]:
    return tuple(_WORDS.findall(value.lower()))


def _stem(value: str) -> str:
    value = value.lower()
    for suffix in ("ing", "ed"):
        if value.endswith(suffix) and len(value) > len(suffix) + 2:
            value = value[: -len(suffix)]
            break
    return value[:-1] if value.endswith("e") and len(value) > 3 else value


def _latest_user_turn(value: str) -> str:
    if not value.startswith(_CONTEXT_PREFIX) or _USER_MARKER not in value:
        return value.strip()
    latest = value.rsplit(_USER_MARKER, 1)[1]
    if _CONTEXT_TRAILER in latest:
        latest = latest.split(_CONTEXT_TRAILER, 1)[0]
    return latest.strip() or value.strip()


class OpenAIResponsesAgentModelGateway(BaseGateway):
    """Strict function-call planner with registry-derived action precedence."""

    def _action_scope(self, request: str, actions: tuple[AgentActionDefinition, ...]) -> tuple[AgentActionDefinition, ...]:
        tokens = list(_words(_latest_user_turn(request)))
        while tokens and tokens[0] in _PREFIX:
            tokens.pop(0)
        if not tokens:
            return ()
        verb = _stem(tokens[0])
        candidates = [item for item in actions if _stem(_words(item.name)[0]) == verb]
        if not candidates:
            return ()
        request_words = set(tokens[1:])
        scored = []
        for item in candidates:
            cues = {word for word in _words(item.name)[1:] if word not in _GENERIC}
            scored.append((len(cues & request_words), item))
        best = max(score for score, _ in scored)
        return tuple(item for score, item in scored if score == best)

    def _build_plan_request_payload(self, *, user_request: str, available_tools: tuple[AgentToolDefinition, ...], available_actions: tuple[AgentActionDefinition, ...]) -> dict[str, Any]:
        scoped_actions = self._action_scope(user_request, available_actions)
        actions = scoped_actions or available_actions
        functions = [] if scoped_actions else [self._function(_READ + item.name, "READ ONLY. " + item.description, item.required_argument_names) for item in available_tools]
        functions += [self._function(_ACTION + item.name, "DRY-RUN PROPOSAL ONLY. " + item.description, item.required_argument_names) for item in actions]
        functions.append({
            "type": "function", "name": _CLARIFY,
            "description": "Ask for required business values that are missing or ambiguous.",
            "parameters": {"type": "object", "additionalProperties": False, "required": ["question", "missing_fields"], "properties": {"question": {"type": "string"}, "missing_fields": {"type": "array", "items": {"type": "string"}}}},
            "strict": True,
        })
        instruction = "Choose one path: one to five read__ calls, exactly one action__ call, or clarify__request. Actions only prepare reviewable proposals."
        if scoped_actions:
            instruction = "The latest user message is an explicit change command. Choose exactly one offered action__ function, or clarify__request if required values are missing. Use earlier conversation messages only as context. Do not answer with a read."
        return {"model": self._model, "store": False, "max_output_tokens": self._maximum_output_tokens, "parallel_tool_calls": not bool(scoped_actions), "tool_choice": "required", "tools": functions, "input": [{"role": "system", "content": [{"type": "input_text", "text": instruction}]}, {"role": "user", "content": [{"type": "input_text", "text": user_request}]}]}

    def _parse_plan(self, response_payload: dict[str, Any], *, available_tools: tuple[AgentToolDefinition, ...], available_actions: tuple[AgentActionDefinition, ...]) -> AgentPlan:
        try:
            calls = self._calls(response_payload)
            tools = {item.name: item for item in available_tools}
            actions = {item.name: item for item in available_actions}
            reads, proposals, clarifications = [], [], []
            for name, arguments in calls:
                if name.startswith(_READ):
                    op = name[len(_READ):]
                    definition = tools.get(op)
                    if definition is None:
                        self._reject("unknown_read", response_payload, calls)
                    reads.append(AgentToolCall(tool_name=op, arguments=self._select_required_arguments(arguments, set(definition.required_argument_names))))
                elif name.startswith(_ACTION):
                    op = name[len(_ACTION):]
                    definition = actions.get(op)
                    if definition is None:
                        self._reject("unknown_action", response_payload, calls)
                    proposals.append(AgentActionProposalInput(action_name=op, arguments=self._select_required_arguments(arguments, set(definition.required_argument_names))))
                elif name == _CLARIFY:
                    question, fields = arguments.get("question"), arguments.get("missing_fields")
                    if set(arguments) != {"question", "missing_fields"} or not isinstance(question, str) or not question.strip() or not isinstance(fields, list) or not fields or not all(isinstance(item, str) and item.strip() for item in fields):
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
                return AgentPlan(intent="clarification_required", clarification_question=question, missing_fields=fields)
            if proposals:
                if len(calls) != 1:
                    self._reject("mixed_or_multiple_actions", response_payload, calls)
                return AgentPlan(intent="action_proposal", action_proposal=proposals[0])
            if not reads or len(reads) > 5 or len(reads) != len(calls):
                self._reject("invalid_read_plan", response_payload, calls)
            return AgentPlan(intent="read", tool_calls=tuple(reads))
        except AgentModelResponseInvalidError:
            raise
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise AgentModelResponseInvalidError() from exc

    @staticmethod
    def _function(name: str, description: str, arguments: tuple[str, ...]) -> dict[str, Any]:
        return {"type": "function", "name": name, "description": description, "parameters": {"type": "object", "additionalProperties": False, "required": list(arguments), "properties": {item: {"type": "string"} for item in arguments}}, "strict": True}

    def _calls(self, payload: dict[str, Any]) -> tuple[tuple[str, dict[str, Any]], ...]:
        output = payload.get("output")
        if not isinstance(output, list):
            self._reject("missing_output", payload, ())
        calls = []
        for item in output:
            if isinstance(item, dict) and item.get("type") == "function_call":
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
        logger.info("Rejected invalid workplace planner output", extra={"planner_validation_reason": reason, "provider_response_id": payload.get("id"), "model": self._model, "function_names": [name for name, _ in calls]})
        raise AgentModelResponseInvalidError()
