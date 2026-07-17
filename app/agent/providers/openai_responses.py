from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
from pydantic import ValidationError

from app.agent.contracts import AgentPlan, AgentToolDefinition
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
    ) -> AgentPlan:
        request_payload = self._build_request_payload(
            user_request=user_request,
            available_tools=available_tools,
        )
        response_payload = await self._post_with_retries(request_payload)
        return self._parse_plan(response_payload)

    def _build_request_payload(
        self,
        *,
        user_request: str,
        available_tools: tuple[AgentToolDefinition, ...],
    ) -> dict[str, Any]:
        tool_catalog = [
            {
                "name": tool_definition.name,
                "description": tool_definition.description,
                "required_argument_names": list(
                    tool_definition.required_argument_names
                ),
            }
            for tool_definition in available_tools
        ]
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
                                "Create a read-only tool plan. Use only tools from the "
                                "provided catalog. Never invent tools or arguments. Never "
                                "include organization_id, user_id, roles, permissions, or "
                                "authorization decisions. Return between one and five calls."
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
                                },
                                separators=(",", ":"),
                            ),
                        }
                    ],
                },
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "read_only_agent_plan",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["tool_calls"],
                        "properties": {
                            "tool_calls": {
                                "type": "array",
                                "minItems": 1,
                                "maxItems": 5,
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "required": ["tool_name", "arguments"],
                                    "properties": {
                                        "tool_name": {"type": "string"},
                                        "arguments": {
                                            "type": "object",
                                            "additionalProperties": {"type": "string"},
                                        },
                                    },
                                },
                            }
                        },
                    },
                }
            },
        }

    async def _post_with_retries(
        self,
        request_payload: dict[str, Any],
    ) -> dict[str, Any]:
        owns_http_client = self._http_client is None
        http_client = self._http_client or httpx.AsyncClient(
            timeout=httpx.Timeout(self._timeout_seconds)
        )
        try:
            for attempt_number in range(1, self._maximum_attempts + 1):
                try:
                    response = await http_client.post(
                        self._endpoint,
                        headers={
                            "Authorization": f"Bearer {self._api_key}",
                            "Content-Type": "application/json",
                        },
                        json=request_payload,
                    )
                except (httpx.TimeoutException, httpx.NetworkError) as exception:
                    if attempt_number == self._maximum_attempts:
                        raise AgentModelRequestFailedError() from exception
                    await asyncio.sleep(self._retry_delay_seconds)
                    continue

                if response.status_code in _RETRYABLE_STATUS_CODES:
                    if attempt_number == self._maximum_attempts:
                        raise AgentModelRequestFailedError()
                    await asyncio.sleep(self._retry_delay_seconds)
                    continue

                if response.is_error:
                    raise AgentModelRequestFailedError()

                try:
                    response_payload = response.json()
                except ValueError as exception:
                    raise AgentModelResponseInvalidError() from exception

                if not isinstance(response_payload, dict):
                    raise AgentModelResponseInvalidError()
                return response_payload
        finally:
            if owns_http_client:
                await http_client.aclose()

        raise AgentModelRequestFailedError()

    def _parse_plan(self, response_payload: dict[str, Any]) -> AgentPlan:
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
                if not isinstance(output_text, str):
                    raise AgentModelResponseInvalidError()
                try:
                    plan_payload = json.loads(output_text)
                    return AgentPlan.model_validate(plan_payload)
                except (json.JSONDecodeError, ValidationError) as exception:
                    raise AgentModelResponseInvalidError() from exception

        raise AgentModelResponseInvalidError()
