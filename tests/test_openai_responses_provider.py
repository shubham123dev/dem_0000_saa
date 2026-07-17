from __future__ import annotations

import json

import httpx
import pytest

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


def response_payload(plan: dict) -> dict:
    return {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": json.dumps(plan),
                    }
                ],
            }
        ]
    }


async def test_provider_builds_safe_structured_request_and_parses_plan() -> None:
    captured_request = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request.update(json.loads(request.content))
        assert request.headers["authorization"] == "Bearer test-key"
        return httpx.Response(
            200,
            json=response_payload(
                {
                    "tool_calls": [
                        {
                            "tool_name": "get_organization_profile",
                            "arguments": {"report_id": None},
                        }
                    ]
                }
            ),
        )

    gateway = build_gateway(httpx.MockTransport(handler))
    plan = await gateway.create_plan(
        user_request="Show the profile for org_request_secret",
        available_tools=(
            AgentToolDefinition(
                name="get_organization_profile",
                description="Read the profile.",
            ),
        ),
    )

    assert plan.tool_calls[0].tool_name == "get_organization_profile"
    assert plan.tool_calls[0].arguments == {}
    assert captured_request["store"] is False
    assert captured_request["text"]["format"]["strict"] is True
    assert "org_sandbox_001" not in json.dumps(captured_request)
    await gateway._http_client.aclose()


async def test_provider_preserves_required_report_argument() -> None:
    gateway = build_gateway(
        httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json=response_payload(
                    {
                        "tool_calls": [
                            {
                                "tool_name": "check_organization_report_access",
                                "arguments": {"report_id": "rpt_market_001"},
                            }
                        ]
                    }
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
    )

    assert plan.tool_calls[0].arguments == {"report_id": "rpt_market_001"}
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
            json=response_payload(
                {
                    "tool_calls": [
                        {
                            "tool_name": "list_organization_reports",
                            "arguments": {"report_id": None},
                        }
                    ]
                }
            ),
        )

    gateway = build_gateway(httpx.MockTransport(handler))
    plan = await gateway.create_plan(
        user_request="List reports",
        available_tools=(
            AgentToolDefinition(
                name="list_organization_reports",
                description="List reports.",
            ),
        ),
    )

    assert call_count == 2
    assert plan.tool_calls[0].tool_name == "list_organization_reports"
    await gateway._http_client.aclose()


async def test_provider_stops_after_bounded_retry_attempts() -> None:
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(429, json={"error": "rate_limited"})

    gateway = build_gateway(httpx.MockTransport(handler), maximum_attempts=3)

    with pytest.raises(AgentModelRequestFailedError):
        await gateway.create_plan(
            user_request="Show profile",
            available_tools=(
                AgentToolDefinition(
                    name="get_organization_profile",
                    description="Read profile.",
                ),
            ),
        )

    assert call_count == 3
    await gateway._http_client.aclose()


async def test_provider_does_not_retry_non_retryable_failure() -> None:
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(401, json={"error": "invalid_key"})

    gateway = build_gateway(httpx.MockTransport(handler), maximum_attempts=3)

    with pytest.raises(AgentModelRequestFailedError):
        await gateway.create_plan(
            user_request="Show profile",
            available_tools=(
                AgentToolDefinition(
                    name="get_organization_profile",
                    description="Read profile.",
                ),
            ),
        )

    assert call_count == 1
    await gateway._http_client.aclose()


async def test_provider_rejects_malformed_structured_output() -> None:
    gateway = build_gateway(
        httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "output": [
                        {
                            "type": "message",
                            "content": [
                                {"type": "output_text", "text": "not-json"}
                            ],
                        }
                    ]
                },
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
        )

    await gateway._http_client.aclose()


async def test_provider_retries_timeout_and_reports_failure() -> None:
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        raise httpx.ReadTimeout("timeout", request=request)

    gateway = build_gateway(httpx.MockTransport(handler), maximum_attempts=2)

    with pytest.raises(AgentModelRequestFailedError):
        await gateway.create_plan(
            user_request="Show profile",
            available_tools=(
                AgentToolDefinition(
                    name="get_organization_profile",
                    description="Read profile.",
                ),
            ),
        )

    assert call_count == 2
    await gateway._http_client.aclose()
