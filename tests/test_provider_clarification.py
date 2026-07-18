from __future__ import annotations

import json

import httpx

from app.agent.action_registry import AgentActionRegistry
from app.agent.tool_registry import ReadOnlyAgentToolRegistry
from app.agent.providers.openai_responses import OpenAIResponsesAgentModelGateway


def _response(plan: dict) -> dict:
    return {
        "status": "completed",
        "output": [
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": json.dumps(plan)}
                ],
            }
        ],
    }


async def test_provider_sends_resource_catalog_and_parses_clarification() -> None:
    captured = {}
    actions = AgentActionRegistry().list_definitions()
    action_argument_names = sorted(
        {
            argument
            for definition in actions
            for argument in definition.required_argument_names
        }
    )

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json=_response(
                {
                    "intent": "clarification_required",
                    "tool_calls": [],
                    "action_name": None,
                    "action_arguments": {
                        name: None for name in action_argument_names
                    },
                    "clarification_question": "Which market should be granted?",
                    "missing_fields": ["market_id"],
                }
            ),
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    gateway = OpenAIResponsesAgentModelGateway(
        api_key="test-key",
        model="test-model",
        endpoint="https://provider.test/v1/responses",
        timeout_seconds=1,
        maximum_attempts=1,
        retry_delay_seconds=0,
        maximum_output_tokens=500,
        http_client=client,
    )
    plan = await gateway.create_plan(
        user_request="Grant market access",
        available_tools=ReadOnlyAgentToolRegistry().list_tool_definitions(),
        available_actions=actions,
    )
    assert plan.intent == "clarification_required"
    assert plan.missing_fields == ("market_id",)
    assert plan.clarification_question == "Which market should be granted?"
    request_text = json.dumps(captured).lower()
    assert "resource_catalog" in request_text
    assert "workplace_setting" in request_text
    assert "password" not in request_text
    schema = captured["text"]["format"]["schema"]
    assert "clarification_required" in schema["properties"]["intent"]["enum"]
    assert {"clarification_question", "missing_fields"}.issubset(
        schema["required"]
    )
    await client.aclose()
