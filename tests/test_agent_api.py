from __future__ import annotations

from datetime import datetime, timezone

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.contracts import AgentPlan, AgentToolCall
from app.api.agent_dependencies import get_agent_model_gateway
from app.db.orm_models import OrganizationORM
from app.main import app

AGENT_QUERY_URL = "/workplace/organizations/org_sandbox_001/agent/query"
EXPECTED_ACTION_NAMES = {
    "update_organization_contact_email",
    "invite_organization_user",
    "assign_organization_seat",
    "grant_organization_report_access",
}


class FixedAgentModelGateway:
    def __init__(self, agent_plan: AgentPlan) -> None:
        self.agent_plan = agent_plan
        self.received_user_request: str | None = None
        self.received_tool_names: tuple[str, ...] = ()
        self.received_action_names: tuple[str, ...] = ()
        self.plan_call_count = 0

    async def create_plan(self, *, user_request: str, available_tools, available_actions):
        self.plan_call_count += 1
        self.received_user_request = user_request
        self.received_tool_names = tuple(item.name for item in available_tools)
        self.received_action_names = tuple(item.name for item in available_actions)
        return self.agent_plan


def override_agent_model(agent_plan: AgentPlan) -> FixedAgentModelGateway:
    gateway = FixedAgentModelGateway(agent_plan)
    app.dependency_overrides[get_agent_model_gateway] = lambda: gateway
    return gateway


async def test_agent_query_returns_grounded_profile_result(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    gateway = override_agent_model(
        AgentPlan(tool_calls=(AgentToolCall(tool_name="get_organization_profile"),))
    )
    response = await client.post(
        AGENT_QUERY_URL,
        headers=admin_headers,
        json={"query": "Show the organization profile"},
    )

    assert response.status_code == 200
    assert gateway.plan_call_count == 1
    assert set(gateway.received_tool_names) == {
        "get_organization_profile",
        "list_organization_users",
        "get_organization_seat_summary",
        "list_organization_reports",
        "check_organization_report_access",
        "get_organization_audit_log",
    }
    assert set(gateway.received_action_names) == EXPECTED_ACTION_NAMES
    body = response.json()
    assert body["mode"] == "read"
    assert body["action_proposal"] is None
    assert body["organization_id"] == "org_sandbox_001"
    assert body["results"][0]["tool_name"] == "get_organization_profile"
    assert body["results"][0]["data"]["id"] == "org_sandbox_001"


async def test_agent_query_requires_authentication(client: AsyncClient) -> None:
    override_agent_model(
        AgentPlan(tool_calls=(AgentToolCall(tool_name="get_organization_profile"),))
    )
    response = await client.post(
        AGENT_QUERY_URL,
        json={"query": "Show the organization profile"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"


async def test_agent_query_uses_backend_organization_scope(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    now = datetime.now(timezone.utc)
    db_session.add(
        OrganizationORM(
            id="org_sandbox_unavailable",
            display_name="Unavailable Sandbox",
            legal_name=None,
            contact_email=None,
            environment="sandbox",
            status="active",
            version=1,
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.commit()
    override_agent_model(
        AgentPlan(tool_calls=(AgentToolCall(tool_name="get_organization_profile"),))
    )
    response = await client.post(
        "/workplace/organizations/org_sandbox_unavailable/agent/query",
        headers=admin_headers,
        json={"query": "Show that organization"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "organization_access_denied"


async def test_agent_query_rejects_model_write_tool(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    override_agent_model(
        AgentPlan(tool_calls=(AgentToolCall(tool_name="delete_organization"),))
    )
    response = await client.post(
        AGENT_QUERY_URL,
        headers=admin_headers,
        json={"query": "Delete the organization"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "agent_tool_call_invalid"


async def test_agent_query_rejects_model_supplied_identity(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    override_agent_model(
        AgentPlan(
            tool_calls=(
                AgentToolCall(
                    tool_name="get_organization_profile",
                    arguments={"organization_id": "org_other_001"},
                ),
            )
        )
    )
    response = await client.post(
        AGENT_QUERY_URL,
        headers=admin_headers,
        json={"query": "Show another organization"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "agent_tool_call_invalid"


async def test_agent_query_returns_unavailable_without_configured_model(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    response = await client.post(
        AGENT_QUERY_URL,
        headers=admin_headers,
        json={"query": "Show the organization profile"},
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "agent_model_unavailable"


async def test_agent_query_rejects_invalid_request_bodies(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    for request_body in (
        {"query": ""},
        {"query": "   "},
        {"query": "x" * 4001},
        {"query": "Show profile", "organization_id": "org_other_001"},
    ):
        response = await client.post(
            AGENT_QUERY_URL,
            headers=admin_headers,
            json=request_body,
        )
        assert response.status_code == 422
        assert response.json()["error"]["message"] == "Request validation failed."
