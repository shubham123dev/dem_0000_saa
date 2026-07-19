from __future__ import annotations

import json

import httpx
import pytest

from app.agent.action_registry import AgentActionRegistry
from app.agent.contracts import AgentToolDefinition
from app.agent.errors import AgentModelResponseInvalidError
from app.agent.providers.workplace_openai_responses import OpenAIResponsesAgentModelGateway


def _actions():
    return AgentActionRegistry().list_model_definitions()


def _response(*calls: tuple[str, dict]) -> dict:
    return {
        "id": "resp_test_planner",
        "status": "completed",
        "output": [
            {
                "type": "function_call",
                "status": "completed",
                "name": name,
                "arguments": json.dumps(arguments),
            }
            for name, arguments in calls
        ],
    }


def _gateway(payload: dict, captured: dict | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        if captured is not None:
            captured.update(json.loads(request.content))
        return httpx.Response(200, json=payload)

    return OpenAIResponsesAgentModelGateway(
        api_key="test-key",
        model="test-model",
        endpoint="https://provider.test/v1/responses",
        timeout_seconds=1,
        maximum_attempts=1,
        retry_delay_seconds=0,
        maximum_output_tokens=500,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )


def _tools():
    return (
        AgentToolDefinition(
            name="get_organization_profile",
            description="Read the profile.",
        ),
        AgentToolDefinition(
            name="check_organization_report_access",
            description="Check report access.",
            required_argument_names=("report_id",),
        ),
    )


async def test_builds_registry_derived_strict_function_catalogue() -> None:
    captured: dict = {}
    gateway = _gateway(
        _response(("read__get_organization_profile", {})),
        captured,
    )
    plan = await gateway.create_plan(
        user_request="Show the profile",
        available_tools=_tools(),
        available_actions=_actions(),
    )
    assert plan.intent == "read"
    assert captured["tool_choice"] == "required"
    assert captured["parallel_tool_calls"] is True
    names = {item["name"] for item in captured["tools"]}
    assert "read__get_organization_profile" in names
    assert "action__invite_organization_user" in names
    assert "clarify__request" in names
    assert all(item["strict"] is True for item in captured["tools"])
    await gateway._http_client.aclose()


async def test_exact_invitation_query_parses_to_invite_proposal() -> None:
    gateway = _gateway(
        _response(
            (
                "action__invite_organization_user",
                {
                    "email": "demo.analyst.20260719@example.test",
                    "display_name": "Demo Analyst",
                    "role": "sandbox_reader",
                },
            )
        )
    )
    plan = await gateway.create_plan(
        user_request=(
            "Invite a user named Demo Analyst with email "
            "demo.analyst.20260719@example.test as sandbox_reader."
        ),
        available_tools=_tools(),
        available_actions=_actions(),
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


async def test_parses_multiple_reads_and_clarification() -> None:
    read_gateway = _gateway(
        _response(
            ("read__get_organization_profile", {}),
            ("read__check_organization_report_access", {"report_id": "rpt_market_001"}),
        )
    )
    read_plan = await read_gateway.create_plan(
        user_request="Show profile and report access",
        available_tools=_tools(),
        available_actions=_actions(),
    )
    assert [item.tool_name for item in read_plan.tool_calls] == [
        "get_organization_profile",
        "check_organization_report_access",
    ]
    await read_gateway._http_client.aclose()

    clarification_gateway = _gateway(
        _response(
            (
                "clarify__request",
                {
                    "question": "What email and role should the user have?",
                    "missing_fields": ["email", "role"],
                },
            )
        )
    )
    clarification = await clarification_gateway.create_plan(
        user_request="Invite a user",
        available_tools=_tools(),
        available_actions=_actions(),
    )
    assert clarification.intent == "clarification_required"
    assert clarification.missing_fields == ("email", "role")
    await clarification_gateway._http_client.aclose()


@pytest.mark.parametrize(
    "payload",
    [
        _response(
            ("read__get_organization_profile", {}),
            (
                "action__invite_organization_user",
                {"email": "a@example.test", "display_name": "A", "role": "sandbox_reader"},
            ),
        ),
        _response(("action__invented_action", {})),
        _response(
            (
                "action__invite_organization_user",
                {"display_name": "A", "role": "sandbox_reader"},
            )
        ),
        _response(
            ("clarify__request", {"question": "Which user?", "missing_fields": ["user_id"]}),
            ("read__get_organization_profile", {}),
        ),
        {"id": "resp_empty", "status": "completed", "output": []},
    ],
)
async def test_rejects_mixed_unknown_incomplete_or_empty_plans(payload: dict) -> None:
    gateway = _gateway(payload)
    with pytest.raises(AgentModelResponseInvalidError):
        await gateway.create_plan(
            user_request="Process safely",
            available_tools=_tools(),
            available_actions=_actions(),
        )
    await gateway._http_client.aclose()
