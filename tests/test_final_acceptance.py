from __future__ import annotations

from httpx import AsyncClient

from app.agent.action_contracts import AgentActionProposalInput
from app.agent.contracts import AgentPlan, AgentToolCall
from app.api.agent_dependencies import get_agent_model_gateway
from app.main import app

ORGANIZATION_ID = "org_sandbox_001"
QUERY_URL = f"/workplace/organizations/{ORGANIZATION_ID}/agent/query"


class _FinalPlanGateway:
    def __init__(self, plan: AgentPlan) -> None:
        self.plan = plan
        self.available_action_names: tuple[str, ...] = ()
        self.available_tool_names: tuple[str, ...] = ()

    async def create_plan(self, *, user_request, available_tools, available_actions):
        self.available_action_names = tuple(item.name for item in available_actions)
        self.available_tool_names = tuple(item.name for item in available_tools)
        return self.plan


def _override(plan: AgentPlan) -> _FinalPlanGateway:
    gateway = _FinalPlanGateway(plan)
    app.dependency_overrides[get_agent_model_gateway] = lambda: gateway
    return gateway


async def test_final_readiness_and_capability_counts(
    client: AsyncClient,
) -> None:
    readiness = await client.get("/ready/details")
    assert readiness.status_code == 200
    body = readiness.json()
    assert body["migration"]["expected"] == "0015_workplace_workflows"
    assert body["migration"]["current"] in (
        "0015_workplace_workflows", None
    )
    assert body["actions"] == {"registered": 43, "handlers": 43}
    assert body["read_tools"] == {"registered": 20}
    assert body["checks"]["workflow_schema_supported"] is True
    assert body["checks"]["workplace_workflow_permission_seeded"] is True
    assert body["checks"]["agent_resource_tools_registered"] is True
    assert body["checks"]["registry_handler_parity"] is True
    assert body["checks"]["internal_rollback_hidden_from_model"] is True

    capabilities = await client.get("/workplace/capabilities")
    assert capabilities.status_code == 200
    payload = capabilities.json()
    assert len(payload["read_tools"]) == 20
    assert len(payload["write_actions"]) == 43
    internal = next(
        item
        for item in payload["write_actions"]
        if item["name"] == "restore_workplace_resource_snapshots"
    )
    assert internal["minimum_approvals"] == 2
    assert internal["self_approval_allowed"] is False
    assert internal["model_selectable"] is False


async def test_natural_language_pipeline_can_select_final_relationship_tool(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    gateway = _override(
        AgentPlan(
            tool_calls=(
                AgentToolCall(
                    tool_name="list_related_workplace_resources",
                    arguments={
                        "source_resource_type": "organization",
                        "source_resource_id": ORGANIZATION_ID,
                        "relationship": "memberships",
                    },
                ),
            )
        )
    )
    response = await client.post(
        QUERY_URL,
        headers=admin_headers,
        json={"query": "Show the users related to this organization."},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["mode"] == "read"
    assert body["results"][0]["tool_name"] == (
        "list_related_workplace_resources"
    )
    assert body["results"][0]["data"]["count"] >= 1
    assert len(gateway.available_tool_names) == 20


async def test_natural_language_pipeline_can_propose_final_workflow_only(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    gateway = _override(
        AgentPlan(
            intent="action_proposal",
            action_proposal=AgentActionProposalInput(
                action_name="onboard_organization_user",
                arguments={
                    "email": "nl.workflow@example.test",
                    "display_name": "Natural Language Workflow",
                    "role": "sandbox_reader",
                    "seat_type": "none",
                },
            ),
        )
    )
    response = await client.post(
        QUERY_URL,
        headers=admin_headers,
        json={"query": "Onboard a reader without assigning a seat."},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["mode"] == "action_proposal"
    assert body["action_proposal"]["action_name"] == (
        "onboard_organization_user"
    )
    assert body["action_proposal"]["status"] == "pending_approval"
    assert len(gateway.available_action_names) == 42
    assert "restore_workplace_resource_snapshots" not in (
        gateway.available_action_names
    )


async def test_internal_snapshot_restore_cannot_be_proposed_directly(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    response = await client.post(
        f"/workplace/organizations/{ORGANIZATION_ID}/agent/actions/propose",
        headers=admin_headers,
        json={
            "action_name": "restore_workplace_resource_snapshots",
            "arguments": {
                "resource_type": "workplace_setting",
                "snapshots_json": "[]",
            },
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "agent_action_invalid"
