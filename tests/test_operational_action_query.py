from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.action_contracts import AgentActionProposalInput
from app.agent.contracts import AgentPlan
from app.api.agent_dependencies import get_agent_answer_gateway, get_agent_model_gateway
from app.db.orm_models import SeatAssignmentORM
from app.main import app

QUERY_URL = "/workplace/organizations/org_sandbox_001/agent/query"


class SeatProposalGateway:
    def __init__(self) -> None:
        self.plan_calls = 0
        self.answer_calls = 0

    async def create_plan(self, *, user_request: str, available_tools, available_actions):
        self.plan_calls += 1
        assert "assign_organization_seat" in {
            definition.name for definition in available_actions
        }
        return AgentPlan(
            intent="action_proposal",
            action_proposal=AgentActionProposalInput(
                action_name="assign_organization_seat",
                arguments={"user_id": "usr_member_003", "seat_type": "standard"},
            ),
        )

    async def create_answer(self, *, user_request: str, evidence):
        self.answer_calls += 1
        raise AssertionError("Operational proposals must not trigger synthesis")


async def test_natural_language_onboarding_creates_dry_run_without_mutation(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    gateway = SeatProposalGateway()
    app.dependency_overrides[get_agent_model_gateway] = lambda: gateway
    app.dependency_overrides[get_agent_answer_gateway] = lambda: gateway

    response = await client.post(
        QUERY_URL,
        headers=admin_headers,
        json={"query": "Assign a standard seat to the unseated member"},
    )

    assert response.status_code == 200
    body = response.json()
    assert gateway.plan_calls == 1
    assert gateway.answer_calls == 0
    assert body["mode"] == "action_proposal"
    assert body["action_proposal"]["action_name"] == "assign_organization_seat"
    assert body["action_proposal"]["status"] == "pending_approval"
    assignment = await db_session.scalar(
        select(SeatAssignmentORM).where(
            SeatAssignmentORM.organization_id == "org_sandbox_001",
            SeatAssignmentORM.user_id == "usr_member_003",
            SeatAssignmentORM.status == "active",
        )
    )
    assert assignment is None
