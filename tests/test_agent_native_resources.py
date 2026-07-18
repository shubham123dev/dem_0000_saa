from __future__ import annotations

import json

from httpx import AsyncClient

from app.agent.action_contracts import AgentActionProposalInput
from app.agent.contracts import AgentPlan, AgentToolCall
from app.agent.tool_registry import ReadOnlyAgentToolRegistry
from app.api.agent_dependencies import get_agent_model_gateway
from app.main import app

AGENT_QUERY_URL = "/workplace/organizations/org_sandbox_001/agent/query"


class FixedAgentModelGateway:
    def __init__(self, plan: AgentPlan) -> None:
        self._plan = plan

    async def create_plan(self, *, user_request, available_tools, available_actions):
        return self._plan


def _override(plan: AgentPlan) -> None:
    app.dependency_overrides[get_agent_model_gateway] = lambda: FixedAgentModelGateway(
        plan
    )


def test_agent_tool_registry_publishes_safe_resource_catalog() -> None:
    definitions = ReadOnlyAgentToolRegistry().list_tool_definitions()
    assert len(definitions) == 16
    by_name = {item.name: item for item in definitions}
    catalog = by_name["list_workplace_resource_types"].metadata["resource_catalog"]
    by_resource = {item["resource_type"]: item for item in catalog}
    assert "workplace_setting" in by_resource
    assert "user" in by_resource
    assert "report" in by_resource
    assert "role_permission" in by_resource
    organization_fields = {
        item["name"]: item for item in by_resource["organization"]["fields"]
    }
    assert organization_fields["contact_email"]["editable"] is False
    assert organization_fields["display_name"]["editable"] is False
    serialized = json.dumps(catalog).lower()
    assert "password" not in serialized
    assert "__tablename__" not in serialized
    assert "database_url" not in serialized


async def test_agent_can_list_and_search_registered_resources(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    _override(
        AgentPlan(
            tool_calls=(
                AgentToolCall(tool_name="list_workplace_resource_types"),
            )
        )
    )
    listed = await client.post(
        AGENT_QUERY_URL,
        headers=admin_headers,
        json={"query": "What workplace resources can you manage?"},
    )
    assert listed.status_code == 200, listed.text
    listed_body = listed.json()
    assert listed_body["mode"] == "read"
    result = listed_body["results"][0]
    assert result["tool_name"] == "list_workplace_resource_types"
    resource_types = {
        item["resource_type"] for item in result["data"]["resources"]
    }
    assert {"organization", "workplace_setting", "user", "report"}.issubset(
        resource_types
    )

    _override(
        AgentPlan(
            tool_calls=(
                AgentToolCall(
                    tool_name="search_workplace_resources",
                    arguments={
                        "resource_type": "organization",
                        "filters_json": json.dumps(
                            {"id": "org_sandbox_001"},
                            separators=(",", ":"),
                        ),
                    },
                ),
            )
        )
    )
    searched = await client.post(
        AGENT_QUERY_URL,
        headers=admin_headers,
        json={"query": "Find this organization."},
    )
    assert searched.status_code == 200, searched.text
    search_data = searched.json()["results"][0]["data"]
    assert search_data["total"] == 1
    assert search_data["items"][0]["id"] == "org_sandbox_001"


async def test_agent_returns_formal_clarification_without_guessing(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    _override(
        AgentPlan(
            intent="clarification_required",
            clarification_question="Which market should be granted?",
            missing_fields=("market_id",),
        )
    )
    response = await client.post(
        AGENT_QUERY_URL,
        headers=admin_headers,
        json={"query": "Grant market access."},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["mode"] == "clarification_required"
    assert body["answer"] == "Which market should be granted?"
    assert body["missing_fields"] == ["market_id"]
    assert body["results"] == []
    assert body["action_proposal"] is None


async def test_agent_canonicalizes_generic_contact_update_to_bridge_action(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    _override(
        AgentPlan(
            intent="action_proposal",
            action_proposal=AgentActionProposalInput(
                action_name="update_workplace_resource",
                arguments={
                    "resource_type": "organization",
                    "resource_id": "org_sandbox_001",
                    "changes_json": json.dumps(
                        {"contact_email": "canonical@example.test"}
                    ),
                },
            ),
        )
    )
    response = await client.post(
        AGENT_QUERY_URL,
        headers=admin_headers,
        json={"query": "Change the organization contact email."},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["mode"] == "action_proposal"
    assert body["action_proposal"]["action_name"] == (
        "update_organization_contact_email"
    )
