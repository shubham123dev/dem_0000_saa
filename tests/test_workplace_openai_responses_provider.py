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
        "id": "resp_test_planner",
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


def _complete_invite_plan() -> dict[str, object]:
    arguments = _empty_action_arguments()
    arguments.update(
        {
            "email": "demo.analyst.20260719@example.test",
            "display_name": "Demo Analyst",
            "role": "sandbox_reader",
        }
    )
    return {
        "intent": "action_proposal",
        "tool_calls": [],
        "action_name": "invite_organization_user",
        "action_arguments": arguments,
        "clarification_question": (
            "Would you like me to explain what happens after approval?"
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


async def test_accepts_nonblocking_question_on_complete_invitation_plan() -> None:
    gateway = _gateway(_complete_invite_plan())

    plan = await gateway.create_plan(
        user_request=(
            "Invite a user named Demo Analyst with email "
            "demo.analyst.20260719@example.test as sandbox_reader."
        ),
        available_tools=(
            AgentToolDefinition(
                name="get_organization_profile",
                description="Read the profile.",
            ),
        ),
        available_actions=_available_actions(),
    )

    assert plan.intent == "action_proposal"
    assert plan.action_proposal is not None
    assert plan.action_proposal.action_name == "invite_organization_user"
    assert plan.action_proposal.arguments == {
        "email": "demo.analyst.20260719@example.test",
        "display_name": "Demo Analyst",
        "role": "sandbox_reader",
    }
    await gateway._http_client.aclose()


@pytest.mark.parametrize(
    "unsafe_variant",
    [
        "missing_field",
        "action_argument",
        "mixed_read_action",
        "unknown_action",
        "missing_required_action_value",
    ],
)
async def test_keeps_rejecting_genuinely_invalid_plans(
    unsafe_variant: str,
) -> None:
    if unsafe_variant in {"missing_field", "action_argument"}:
        plan_payload = _complete_read_plan()
        if unsafe_variant == "missing_field":
            plan_payload["missing_fields"] = ["report_id"]
        else:
            action_arguments = dict(plan_payload["action_arguments"])
            action_arguments["report_id"] = "rpt_market_001"
            plan_payload["action_arguments"] = action_arguments
    else:
        plan_payload = _complete_invite_plan()
        if unsafe_variant == "mixed_read_action":
            plan_payload["tool_calls"] = [
                {
                    "tool_name": "get_organization_profile",
                    "arguments": {},
                }
            ]
        elif unsafe_variant == "unknown_action":
            plan_payload["action_name"] = "invented_user_action"
        else:
            action_arguments = dict(plan_payload["action_arguments"])
            action_arguments["email"] = None
            plan_payload["action_arguments"] = action_arguments

    gateway = _gateway(plan_payload)

    with pytest.raises(AgentModelResponseInvalidError):
        await gateway.create_plan(
            user_request="Process this request safely",
            available_tools=(
                AgentToolDefinition(
                    name="get_organization_profile",
                    description="Read the profile.",
                ),
            ),
            available_actions=_available_actions(),
        )

    await gateway._http_client.aclose()
