from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
from pydantic import ValidationError

from app.agent.action_contracts import AgentActionDefinition, AgentActionProposalInput
from app.agent.answer_contracts import AgentAnswerDraft, AgentEvidenceItem
from app.agent.contracts import AgentPlan, AgentToolCall, AgentToolDefinition
from app.agent.errors import AgentModelRequestFailedError, AgentModelResponseInvalidError

_RETRYABLE_STATUS_CODES = frozenset({408, 409, 429, 500, 502, 503, 504})


class OpenAIResponsesAgentModelGateway:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        endpoint: str,
        timeout_seconds: float,
        maximum_attempts: int,
        retry_delay_seconds: float,
        maximum_output_tokens: int,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._endpoint = endpoint
        self._timeout_seconds = timeout_seconds
        self._maximum_attempts = maximum_attempts
        self._retry_delay_seconds = retry_delay_seconds
        self._maximum_output_tokens = maximum_output_tokens
        self._http_client = http_client

    async def create_plan(
        self,
        *,
        user_request: str,
        available_tools: tuple[AgentToolDefinition, ...],
        available_actions: tuple[AgentActionDefinition, ...],
    ) -> AgentPlan:
        response_payload = await self._post_with_retries(
            self._build_plan_request_payload(
                user_request=user_request,
                available_tools=available_tools,
                available_actions=available_actions,
            )
        )
        return self._parse_plan(
            response_payload,
            available_tools=available_tools,
            available_actions=available_actions,
        )

    async def create_answer(
        self,
        *,
        user_request: str,
        evidence: tuple[AgentEvidenceItem, ...],
    ) -> AgentAnswerDraft:
        response_payload = await self._post_with_retries(
            self._build_answer_request_payload(
                user_request=user_request,
                evidence=evidence,
            )
        )
        return self._parse_answer(response_payload)

    def _build_plan_request_payload(
        self,
        *,
        user_request: str,
        available_tools: tuple[AgentToolDefinition, ...],
        available_actions: tuple[AgentActionDefinition, ...],
    ) -> dict[str, Any]:
        tool_catalog = [
            {
                "name": definition.name,
                "description": definition.description,
                "required_argument_names": list(definition.required_argument_names),
                "metadata": definition.metadata,
            }
            for definition in available_tools
        ]
        action_catalog = [
            {
                "name": definition.name,
                "description": definition.description,
                "required_argument_names": list(definition.required_argument_names),
                "risk_level": definition.risk_level,
                "requires_approval": definition.requires_approval,
                "supports_dry_run": definition.supports_dry_run,
            }
            for definition in available_actions
        ]
        tool_argument_names = self._argument_names(available_tools)
        action_argument_names = self._argument_names(available_actions)
        return {
            "model": self._model,
            "store": False,
            "max_output_tokens": self._maximum_output_tokens,
            "input": [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Choose exactly one intent. For read intent, return one to five "
                                "allowlisted read tool calls and no action. For action_proposal "
                                "intent, return exactly one allowlisted action proposal and no read "
                                "calls. If a required business argument is missing or ambiguous, "
                                "return clarification_required with one concise question and the "
                                "missing field names; never guess identifiers or values. Use the "
                                "backend resource catalog and its canonical routes instead of "
                                "inventing resource types, fields, tools, or actions. Set every union "
                                "argument not required by the selected item to null. Never include "
                                "organization_id, actor_user_id, permissions, approval decisions, "
                                "proposal identifiers, execution commands, or idempotency keys. A "
                                "target user_id or requested membership role may be included only "
                                "when explicitly required by the selected action. An action proposal "
                                "is a dry-run request pending explicit backend approval."
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": json.dumps(
                                {
                                    "request": user_request,
                                    "available_tools": tool_catalog,
                                    "available_actions": action_catalog,
                                },
                                ensure_ascii=False,
                                separators=(",", ":"),
                            ),
                        }
                    ],
                },
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "workplace_agent_plan",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "intent",
                            "tool_calls",
                            "action_name",
                            "action_arguments",
                            "clarification_question",
                            "missing_fields",
                        ],
                        "properties": {
                            "intent": {
                                "type": "string",
                                "enum": [
                                    "read",
                                    "action_proposal",
                                    "clarification_required",
                                ],
                            },
                            "tool_calls": {
                                "type": "array",
                                "maxItems": 5,
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "required": ["tool_name", "arguments"],
                                    "properties": {
                                        "tool_name": {
                                            "type": "string",
                                            "enum": [item.name for item in available_tools],
                                        },
                                        "arguments": self._nullable_argument_schema(
                                            tool_argument_names
                                        ),
                                    },
                                },
                            },
                            "action_name": {
                                "type": ["string", "null"],
                                "enum": [item.name for item in available_actions] + [None],
                            },
                            "action_arguments": self._nullable_argument_schema(
                                action_argument_names
                            ),
                            "clarification_question": {
                                "type": ["string", "null"],
                                "minLength": 1,
                                "maxLength": 500,
                            },
                            "missing_fields": {
                                "type": "array",
                                "maxItems": 8,
                                "items": {"type": "string", "minLength": 1},
                            },
                        },
                    },
                }
            },
        }

    def _build_answer_request_payload(
        self,
        *,
        user_request: str,
        evidence: tuple[AgentEvidenceItem, ...],
    ) -> dict[str, Any]:
        evidence_ids = [item.id for item in evidence]
        return {
            "model": self._model,
            "store": False,
            "max_output_tokens": self._maximum_output_tokens,
            "input": [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Answer only from the supplied authorized evidence. Do not request "
                                "tools, invent facts, change scope, or cite unknown evidence identifiers. "
                                "Cite at least one evidence identifier."
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": json.dumps(
                                {
                                    "request": user_request,
                                    "evidence": [
                                        item.model_dump(mode="json") for item in evidence
                                    ],
                                },
                                ensure_ascii=False,
                                separators=(",", ":"),
                            ),
                        }
                    ],
                },
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "grounded_agent_answer",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["answer", "evidence_ids"],
                        "properties": {
                            "answer": {"type": "string", "minLength": 1},
                            "evidence_ids": {
                                "type": "array",
                                "minItems": 1,
                                "maxItems": 5,
                                "items": {"type": "string", "enum": evidence_ids},
                            },
                        },
                    },
                }
            },
        }

    async def _post_with_retries(self, request_payload: dict[str, Any]) -> dict[str, Any]:
        owns_client = self._http_client is None
        client = self._http_client or httpx.AsyncClient(
            timeout=httpx.Timeout(self._timeout_seconds)
        )
        try:
            for attempt_number in range(1, self._maximum_attempts + 1):
                try:
                    response = await client.post(
                        self._endpoint,
                        headers={
                            "Authorization": f"Bearer {self._api_key}",
                            "Content-Type": "application/json",
                        },
                        json=request_payload,
                    )
                except httpx.RequestError as exception:
                    if attempt_number == self._maximum_attempts:
                        raise AgentModelRequestFailedError() from exception
                    await asyncio.sleep(self._retry_delay_seconds)
                    continue
                if response.status_code in _RETRYABLE_STATUS_CODES:
                    if attempt_number == self._maximum_attempts:
                        raise AgentModelRequestFailedError(
                            f"HTTP {response.status_code} after {attempt_number} attempts: {response.text[:500]}"
                        )
                    await asyncio.sleep(self._retry_delay_seconds)
                    continue
                if response.is_error:
                    raise AgentModelRequestFailedError(
                        f"HTTP {response.status_code}: {response.text[:500]}"
                    )
                try:
                    payload = response.json()
                except ValueError as exception:
                    raise AgentModelResponseInvalidError() from exception
                if not isinstance(payload, dict):
                    raise AgentModelResponseInvalidError()
                if payload.get("status") in {
                    "failed",
                    "incomplete",
                    "cancelled",
                    "in_progress",
                }:
                    raise AgentModelResponseInvalidError()
                return payload
        finally:
            if owns_client:
                await client.aclose()
        raise AgentModelRequestFailedError()

    def _parse_plan(
        self,
        response_payload: dict[str, Any],
        *,
        available_tools: tuple[AgentToolDefinition, ...],
        available_actions: tuple[AgentActionDefinition, ...],
    ) -> AgentPlan:
        try:
            payload = json.loads(self._extract_output_text(response_payload))
            if not isinstance(payload, dict):
                raise AgentModelResponseInvalidError()
            intent = payload.get("intent")
            raw_tool_calls = payload.get("tool_calls")
            action_name = payload.get("action_name")
            action_arguments = payload.get("action_arguments")
            clarification_question = payload.get("clarification_question")
            missing_fields = payload.get("missing_fields", [])
            if (
                not isinstance(raw_tool_calls, list)
                or not isinstance(action_arguments, dict)
                or not isinstance(missing_fields, list)
            ):
                raise AgentModelResponseInvalidError()

            tool_definitions = {item.name: item for item in available_tools}
            action_definitions = {item.name: item for item in available_actions}
            all_tool_arguments = set(self._argument_names(available_tools))
            all_action_arguments = set(self._argument_names(available_actions))

            if intent == "read":
                if (
                    action_name is not None
                    or any(value is not None for value in action_arguments.values())
                    or clarification_question is not None
                    or missing_fields
                ):
                    raise AgentModelResponseInvalidError()
                tool_calls: list[AgentToolCall] = []
                for raw_call in raw_tool_calls:
                    if not isinstance(raw_call, dict):
                        raise AgentModelResponseInvalidError()
                    tool_name = raw_call.get("tool_name")
                    raw_arguments = raw_call.get("arguments")
                    if not isinstance(tool_name, str) or not isinstance(raw_arguments, dict):
                        raise AgentModelResponseInvalidError()
                    definition = tool_definitions.get(tool_name)
                    if definition is None or set(raw_arguments) != all_tool_arguments:
                        raise AgentModelResponseInvalidError()
                    tool_calls.append(
                        AgentToolCall(
                            tool_name=tool_name,
                            arguments=self._select_required_arguments(
                                raw_arguments,
                                set(definition.required_argument_names),
                            ),
                        )
                    )
                return AgentPlan(intent="read", tool_calls=tuple(tool_calls))

            if intent == "action_proposal":
                if (
                    raw_tool_calls
                    or not isinstance(action_name, str)
                    or clarification_question is not None
                    or missing_fields
                ):
                    raise AgentModelResponseInvalidError()
                definition = action_definitions.get(action_name)
                if definition is None or set(action_arguments) != all_action_arguments:
                    raise AgentModelResponseInvalidError()
                return AgentPlan(
                    intent="action_proposal",
                    action_proposal=AgentActionProposalInput(
                        action_name=action_name,
                        arguments=self._select_required_arguments(
                            action_arguments,
                            set(definition.required_argument_names),
                        ),
                    ),
                )
            if intent == "clarification_required":
                if (
                    raw_tool_calls
                    or action_name is not None
                    or any(value is not None for value in action_arguments.values())
                    or not isinstance(clarification_question, str)
                    or not clarification_question.strip()
                    or not missing_fields
                    or not all(
                        isinstance(item, str) and item.strip()
                        for item in missing_fields
                    )
                ):
                    raise AgentModelResponseInvalidError()
                return AgentPlan(
                    intent="clarification_required",
                    clarification_question=clarification_question,
                    missing_fields=tuple(item.strip() for item in missing_fields),
                )
            raise AgentModelResponseInvalidError()
        except (json.JSONDecodeError, ValidationError, TypeError) as exception:
            raise AgentModelResponseInvalidError() from exception

    def _parse_answer(self, response_payload: dict[str, Any]) -> AgentAnswerDraft:
        try:
            payload = json.loads(self._extract_output_text(response_payload))
            return AgentAnswerDraft.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as exception:
            raise AgentModelResponseInvalidError() from exception

    @staticmethod
    def _argument_names(definitions: tuple[Any, ...]) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    argument_name
                    for definition in definitions
                    for argument_name in definition.required_argument_names
                }
            )
        )

    @staticmethod
    def _nullable_argument_schema(argument_names: tuple[str, ...]) -> dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": list(argument_names),
            "properties": {
                name: {"type": ["string", "null"]} for name in argument_names
            },
        }

    @staticmethod
    def _select_required_arguments(
        raw_arguments: dict[str, Any],
        required_argument_names: set[str],
    ) -> dict[str, str]:
        selected: dict[str, str] = {}
        for argument_name, argument_value in raw_arguments.items():
            if argument_name in required_argument_names:
                if not isinstance(argument_value, str) or not argument_value.strip():
                    raise AgentModelResponseInvalidError()
                selected[argument_name] = argument_value
            elif argument_value is not None:
                raise AgentModelResponseInvalidError()
        if set(selected) != required_argument_names:
            raise AgentModelResponseInvalidError()
        return selected

    @staticmethod
    def _extract_output_text(response_payload: dict[str, Any]) -> str:
        output_items = response_payload.get("output")
        if not isinstance(output_items, list):
            raise AgentModelResponseInvalidError()
        for output_item in output_items:
            if not isinstance(output_item, dict):
                continue
            content_items = output_item.get("content")
            if not isinstance(content_items, list):
                continue
            for content_item in content_items:
                if not isinstance(content_item, dict):
                    continue
                if content_item.get("type") != "output_text":
                    continue
                output_text = content_item.get("text")
                if isinstance(output_text, str):
                    return output_text
                raise AgentModelResponseInvalidError()
        raise AgentModelResponseInvalidError()
