from __future__ import annotations

import json

import httpx
import pytest

from app.agent.action_registry import AgentActionRegistry
from app.agent.contracts import AgentToolDefinition
from app.agent.errors import AgentModelRequestFailedError, AgentModelResponseInvalidError
from app.agent.providers.openai_responses import OpenAIResponsesAgentModelGateway


def build_gateway(transport: httpx.AsyncBaseTransport, *, maximum_attempts: int = 2):
    return OpenAIResponsesAgentModelGateway(
        api_key="test-key",
        model="test-model",
        endpoint="https://provider.test/v1/responses",
        timeout_seconds=1,
        maximum_attempts=maximum_attempts,
        retry_delay_seconds=0,
        maximum_output_tokens=500,
        http_client=httpx.AsyncClient(transport=transport),
    )


def available_actions():
    return AgentActionRegistry().list_model_definitions()


def all_action_argument_names() -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                argument_name
                for definition in available_actions()
                for argument_name in definition.required_argument_names
            }
        )
    )


def action_arguments(**selected: str | None) -> dict[str, str | None]:
    payload = {name: None for name in all_action_argument_names()}
    payload.update(selected)
    return payload


def response_payload(plan: dict) -> dict:
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


def read_plan(tool_name: str, report_id: str | None = None) -> dict:
    return {
        "intent": "read",
        "tool_calls": [
            {
                "tool_name": tool_name,
                "arguments": {"report_id": report_id},
            }
        ],
        "action_name": None,
        "action_arguments": action_arguments(),
    }


async def test_provider_builds_registry_derived_safe_schema_and_parses_read() -> None:
    captured_request = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request.update(json.loads(request.content))
        assert request.headers["authorization"] == "Bearer test-key"
        return httpx.Response(
            200,
            json=response_payload(read_plan("get_organization_profile")),
        )

    gateway = build_gateway(httpx.MockTransport(handler))
    plan = await gateway.create_plan(
        user_request="Show the profile for org_request_secret",
        available_tools=(
            AgentToolDefinition(
                name="get_organization_profile",
                description="Read the profile.",
            ),
            AgentToolDefinition(
                name="check_organization_report_access",
                description="Check report access.",
                required_argument_names=("report_id",),
            ),
        ),
        available_actions=available_actions(),
    )

    assert plan.intent == "read"
    assert plan.tool_calls[0].arguments == {}
    assert captured_request["store"] is False
    assert captured_request["text"]["format"]["strict"] is True
    request_text = json.dumps(captured_request)
    for action_name in {
        "update_organization_contact_email",
        "invite_organization_user",
        "assign_organization_seat",
        "grant_organization_report_access",
    }:
        assert action_name in request_text
    assert "organization.profile.update" not in request_text
    assert "org_sandbox_001" not in request_text
    schema = captured_request["text"]["format"]["schema"]
    assert set(schema["properties"]["action_arguments"]["required"]) == set(
        all_action_argument_names()
    )
    await gateway._http_client.aclose()


async def test_provider_preserves_required_report_argument() -> None:
    gateway = build_gateway(
        httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json=response_payload(
                    read_plan("check_organization_report_access", "rpt_market_001")
                ),
            )
        )
    )
    plan = await gateway.create_plan(
        user_request="Check report access",
        available_tools=(
            AgentToolDefinition(
                name="check_organization_report_access",
                description="Check report access.",
                required_argument_names=("report_id",),
            ),
        ),
        available_actions=available_actions(),
    )
    assert plan.tool_calls[0].arguments == {"report_id": "rpt_market_001"}
    await gateway._http_client.aclose()


@pytest.mark.parametrize(
    ("action_name", "selected_arguments"),
    (
        (
            "update_organization_contact_email",
            {"contact_email": "new.operations@example.test"},
        ),
        (
            "invite_organization_user",
            {
                "email": "new.user@example.test",
                "display_name": "New User",
                "role": "sandbox_reader",
            },
        ),
        (
            "assign_organization_seat",
            {"user_id": "usr_member_003", "seat_type": "standard"},
        ),
        (
            "grant_organization_report_access",
            {"report_id": "rpt_market_004", "access_level": "download"},
        ),
    ),
)
async def test_provider_parses_each_registry_action(
    action_name: str,
    selected_arguments: dict[str, str],
) -> None:
    gateway = build_gateway(
        httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json=response_payload(
                    {
                        "intent": "action_proposal",
                        "tool_calls": [],
                        "action_name": action_name,
                        "action_arguments": action_arguments(**selected_arguments),
                    }
                ),
            )
        )
    )
    plan = await gateway.create_plan(
        user_request="Perform the requested operation",
        available_tools=(
            AgentToolDefinition(
                name="get_organization_profile",
                description="Read profile.",
            ),
        ),
        available_actions=available_actions(),
    )
    assert plan.intent == "action_proposal"
    assert plan.action_proposal.action_name == action_name
    assert plan.action_proposal.arguments == selected_arguments
    await gateway._http_client.aclose()


async def test_provider_schema_excludes_execution_and_authorization_state() -> None:
    captured_request = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request.update(json.loads(request.content))
        plan = read_plan("get_organization_profile")
        plan["tool_calls"][0]["arguments"] = {}
        return httpx.Response(
            200,
            json=response_payload(plan),
        )

    gateway = build_gateway(httpx.MockTransport(handler))
    await gateway.create_plan(
        user_request="Show profile",
        available_tools=(
            AgentToolDefinition(
                name="get_organization_profile",
                description="Read profile.",
            ),
        ),
        available_actions=available_actions(),
    )
    schema_text = json.dumps(captured_request["text"]["format"]["schema"])
    for forbidden_name in (
        "approved",
        "idempotency_key",
        "proposal_id",
        "organization_id",
        "actor_user_id",
        "permission",
    ):
        assert f'"{forbidden_name}"' not in schema_text
    await gateway._http_client.aclose()


async def test_provider_rejects_mixed_or_inexact_plans() -> None:
    invalid_plans = (
        {
            "intent": "action_proposal",
            "tool_calls": [
                {
                    "tool_name": "get_organization_profile",
                    "arguments": {"report_id": None},
                }
            ],
            "action_name": "assign_organization_seat",
            "action_arguments": action_arguments(
                user_id="usr_member_003",
                seat_type="standard",
            ),
        },
        {
            "intent": "read",
            "tool_calls": [
                {
                    "tool_name": "get_organization_profile",
                    "arguments": {"report_id": None},
                }
            ],
            "action_name": "update_organization_contact_email",
            "action_arguments": action_arguments(
                contact_email="new.operations@example.test"
            ),
        },
        {
            "intent": "action_proposal",
            "tool_calls": [],
            "action_name": "grant_organization_report_access",
            "action_arguments": action_arguments(report_id="rpt_market_004"),
        },
    )
    for invalid_plan in invalid_plans:
        gateway = build_gateway(
            httpx.MockTransport(
                lambda request, plan=invalid_plan: httpx.Response(
                    200,
                    json=response_payload(plan),
                )
            )
        )
        with pytest.raises(AgentModelResponseInvalidError):
            await gateway.create_plan(
                user_request="Invalid plan",
                available_tools=(
                    AgentToolDefinition(
                        name="get_organization_profile",
                        description="Read profile.",
                    ),
                    AgentToolDefinition(
                        name="check_organization_report_access",
                        description="Check report access.",
                        required_argument_names=("report_id",),
                    ),
                ),
                available_actions=available_actions(),
            )
        await gateway._http_client.aclose()


async def test_provider_retries_retryable_status_then_succeeds() -> None:
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(503, json={"error": "temporary"})
        return httpx.Response(
            200,
            json=response_payload(read_plan("list_organization_reports")),
        )

    gateway = build_gateway(httpx.MockTransport(handler))
    plan = await gateway.create_plan(
        user_request="List reports",
        available_tools=(
            AgentToolDefinition(
                name="list_organization_reports",
                description="List reports.",
            ),
            AgentToolDefinition(
                name="check_organization_report_access",
                description="Check report access.",
                required_argument_names=("report_id",),
            ),
        ),
        available_actions=available_actions(),
    )
    assert call_count == 2
    assert plan.tool_calls[0].tool_name == "list_organization_reports"
    await gateway._http_client.aclose()


async def test_provider_bounds_retries_and_rejects_non_retryable_failure() -> None:
    retry_count = 0

    def retry_handler(request: httpx.Request) -> httpx.Response:
        nonlocal retry_count
        retry_count += 1
        return httpx.Response(429, json={"error": "rate_limited"})

    gateway = build_gateway(httpx.MockTransport(retry_handler), maximum_attempts=3)
    with pytest.raises(AgentModelRequestFailedError):
        await gateway.create_plan(
            user_request="Show profile",
            available_tools=(
                AgentToolDefinition(
                    name="get_organization_profile",
                    description="Read profile.",
                ),
            ),
            available_actions=available_actions(),
        )
    assert retry_count == 3
    await gateway._http_client.aclose()

    non_retry_count = 0

    def non_retry_handler(request: httpx.Request) -> httpx.Response:
        nonlocal non_retry_count
        non_retry_count += 1
        return httpx.Response(401, json={"error": "invalid_key"})

    gateway = build_gateway(
        httpx.MockTransport(non_retry_handler),
        maximum_attempts=3,
    )
    with pytest.raises(AgentModelRequestFailedError):
        await gateway.create_plan(
            user_request="Show profile",
            available_tools=(
                AgentToolDefinition(
                    name="get_organization_profile",
                    description="Read profile.",
                ),
            ),
            available_actions=available_actions(),
        )
    assert non_retry_count == 1
    await gateway._http_client.aclose()


async def test_provider_rejects_malformed_incomplete_and_timeout_responses() -> None:
    for response_json in (
        {
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "not-json"}],
                }
            ]
        },
        {"status": "incomplete", "output": []},
    ):
        gateway = build_gateway(
            httpx.MockTransport(
                lambda request, payload=response_json: httpx.Response(
                    200,
                    json=payload,
                )
            )
        )
        with pytest.raises(AgentModelResponseInvalidError):
            await gateway.create_plan(
                user_request="Show profile",
                available_tools=(
                    AgentToolDefinition(
                        name="get_organization_profile",
                        description="Read profile.",
                    ),
                ),
                available_actions=available_actions(),
            )
        await gateway._http_client.aclose()

    timeout_count = 0

    def timeout_handler(request: httpx.Request) -> httpx.Response:
        nonlocal timeout_count
        timeout_count += 1
        raise httpx.ReadTimeout("timeout", request=request)

    gateway = build_gateway(httpx.MockTransport(timeout_handler), maximum_attempts=2)
    with pytest.raises(AgentModelRequestFailedError):
        await gateway.create_plan(
            user_request="Show profile",
            available_tools=(
                AgentToolDefinition(
                    name="get_organization_profile",
                    description="Read profile.",
                ),
            ),
            available_actions=available_actions(),
        )
    assert timeout_count == 2
    await gateway._http_client.aclose()
