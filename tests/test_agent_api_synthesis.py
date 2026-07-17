from __future__ import annotations

from httpx import AsyncClient

from app.agent.contracts import AgentPlan, AgentToolCall
from app.api.agent_dependencies import get_agent_model_gateway
from app.main import app


class ProfilePlanGateway:
    async def create_plan(
        self,
        *,
        user_request: str,
        available_tools,
        available_actions,
    ):
        return AgentPlan(
            tool_calls=(AgentToolCall(tool_name="get_organization_profile"),)
        )


async def test_agent_api_preserves_results_when_synthesis_is_unavailable(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    app.dependency_overrides[get_agent_model_gateway] = lambda: ProfilePlanGateway()

    response = await client.post(
        "/workplace/organizations/org_sandbox_001/agent/query",
        headers=admin_headers,
        json={"query": "Show the organization profile"},
    )

    assert response.status_code == 200
    response_body = response.json()
    assert response_body["mode"] == "read"
    assert response_body["answer_source"] == "deterministic"
    assert response_body["evidence_ids"] == ["result-1"]
    assert response_body["results"][0]["tool_name"] == "get_organization_profile"
    assert response_body["results"][0]["data"]["id"] == "org_sandbox_001"
