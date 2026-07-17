from __future__ import annotations

from datetime import datetime, timezone

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.contracts import AgentPlan, AgentToolCall
from app.api.agent_dependencies import get_agent_model_gateway
from app.db.orm_models import OrganizationMembershipORM, OrganizationORM
from app.main import app


class CountingPlanGateway:
    def __init__(self) -> None:
        self.call_count = 0

    async def create_plan(self, *, user_request, available_tools, available_actions):
        self.call_count += 1
        return AgentPlan(
            tool_calls=(AgentToolCall(tool_name="get_organization_profile"),)
        )


async def test_outsider_is_rejected_before_provider_call(
    client: AsyncClient,
    outsider_headers: dict[str, str],
) -> None:
    gateway = CountingPlanGateway()
    app.dependency_overrides[get_agent_model_gateway] = lambda: gateway
    response = await client.post(
        "/workplace/organizations/org_sandbox_001/agent/query",
        headers=outsider_headers,
        json={"query": "Show the profile"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "organization_access_denied"
    assert gateway.call_count == 0


async def test_production_and_suspended_organizations_do_not_reach_provider(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    now = datetime.now(timezone.utc)
    for organization_id, environment, status in (
        ("org_preflight_prod", "production", "active"),
        ("org_preflight_suspended", "sandbox", "suspended"),
    ):
        db_session.add(
            OrganizationORM(
                id=organization_id,
                display_name=organization_id,
                legal_name=None,
                contact_email=None,
                environment=environment,
                status=status,
                version=1,
                created_at=now,
                updated_at=now,
            )
        )
        await db_session.flush()
        db_session.add(
            OrganizationMembershipORM(
                organization_id=organization_id,
                user_id="usr_admin_001",
                role="sandbox_admin",
                membership_status="active",
                joined_at=now,
            )
        )
    await db_session.commit()

    gateway = CountingPlanGateway()
    app.dependency_overrides[get_agent_model_gateway] = lambda: gateway
    production_response = await client.post(
        "/workplace/organizations/org_preflight_prod/agent/query",
        headers=admin_headers,
        json={"query": "Show profile"},
    )
    suspended_response = await client.post(
        "/workplace/organizations/org_preflight_suspended/agent/query",
        headers=admin_headers,
        json={"query": "Show profile"},
    )
    assert production_response.status_code == 403
    assert production_response.json()["error"]["code"] == "production_access_blocked"
    assert suspended_response.status_code == 403
    assert suspended_response.json()["error"]["code"] == "organization_suspended"
    assert gateway.call_count == 0
