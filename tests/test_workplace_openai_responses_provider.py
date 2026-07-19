from __future__ import annotations

import json

import httpx
import pytest

from app.agent.action_registry import AgentActionRegistry
from app.agent.contracts import AgentToolDefinition
from app.agent.errors import AgentModelResponseInvalidError
from app.agent.providers.workplace_openai_responses import OpenAIResponsesAgentModelGateway


def _available_actions():
    return AgentActionRegistry().list_model_definitions()


def _empty_action_arguments() -> dict[str, None]:
    return {
        argument_name: None
        for definition in _available_actions()
        for argument_name in definition.required_argument_names
    }


def _response_payload(plan: dict[str, object]) -> dict[str, object]:
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


def _gateway(plan: dict[str, object]) -> OpenAIResponsesAgentModelGateway:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=_response_payload(plan))
    )
    return OpenAIResponsesAgentModelGateway(
        api_key="test-key",
        model="test-model",
        endpoint="https://provider.test/v1/responses",
        timeout_seconds=1,
        maximum_attempts=1,
        retry_delay_seconds=0,
        maximum_output_tokens=500,
        http_client=httpx.AsyncClient(transport=transport),
    )


def _complete_read_plan() -> dict[str, object]:
    return {
        "intent": "read",
        "tool_calls": [
            {
                "tool_name": "get_organization_profile",
                "arguments": {},
            }
        ],
        "action_name": None,
        "action_arguments": _empty_action_arguments(),
        "clarification_question": (
            "Would you like a more detailed breakdown after this summary?"
        ),
        "missing_fields": [],
    }


async def test_accepts_nonblocking_question_on_complete_read_plan() -> None:
    gateway = _gateway(_complete_read_plan())

    plan = await gateway.create_plan(
        user_request="Summarize the organization",
        available_tools=(
            AgentToolDefinition(
                name="get_organization_profile",
                description="Read the profile.",
            ),
        ),
        available_actions=_available_actions(),
    )

    assert plan.intent == "read"
    assert plan.tool_calls[0].tool_name == "get_organization_profile"
    await gateway._http_client.aclose()


@pytest.mark.parametrize("unsafe_variant", ["missing_field", "action_argument"])
async def test_keeps_rejecting_genuinely_mixed_read_plans(
    unsafe_variant: str,
) -> None:
    plan_payload = _complete_read_plan()
    if unsafe_variant == "missing_field":
        plan_payload["missing_fields"] = ["report_id"]
    else:
        action_arguments = dict(plan_payload["action_arguments"])
        action_arguments["report_id"] = "rpt_market_001"
        plan_payload["action_arguments"] = action_arguments

    gateway = _gateway(plan_payload)

    with pytest.raises(AgentModelResponseInvalidError):
        await gateway.create_plan(
            user_request="Summarize the organization",
            available_tools=(
                AgentToolDefinition(
                    name="get_organization_profile",
                    description="Read the profile.",
                ),
            ),
            available_actions=_available_actions(),
        )

    await gateway._http_client.aclose()
