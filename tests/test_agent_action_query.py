from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.action_contracts import AgentActionProposalInput
from app.agent.contracts import AgentPlan
from app.api.agent_dependencies import get_agent_answer_gateway, get_agent_model_gateway
from app.db.action_models import AgentActionProposalORM
from app.db.orm_models import AuditEventORM, OrganizationORM
from app.main import app

ORGANIZATION_ID = "org_sandbox_001"
QUERY_URL = f"/workplace/organizations/{ORGANIZATION_ID}/agent/query"
ACTION_BASE_URL = f"/workplace/organizations/{ORGANIZATION_ID}/agent/actions"
EXPECTED_ACTION_NAMES = {
    "update_organization_contact_email",
    "invite_organization_user",
    "activate_organization_membership",
    "update_organization_member_role",
    "remove_organization_user",
    "assign_organization_seat",
    "revoke_organization_seat",
    "grant_organization_report_access",
    "revoke_organization_report_access",
}


class ActionPlanGateway:
    def __init__(self, contact_email: str = "agent.operations@example.test") -> None:
        self.contact_email = contact_email
        self.plan_call_count = 0
        self.answer_call_count = 0
        self.received_action_names: tuple[str, ...] = ()

    async def create_plan(self, *, user_request: str, available_tools, available_actions) -> AgentPlan:
        self.plan_call_count += 1
        self.received_action_names = tuple(item.name for item in available_actions)
        return AgentPlan(
            intent="action_proposal",
            action_proposal=AgentActionProposalInput(
                action_name="update_organization_contact_email",
                arguments={"contact_email": self.contact_email},
            ),
        )

    async def create_answer(self, *, user_request: str, evidence):
        self.answer_call_count += 1
        raise AssertionError("Action proposals must not trigger answer synthesis")


def override_action_plan_gateway() -> ActionPlanGateway:
    gateway = ActionPlanGateway()
    app.dependency_overrides[get_agent_model_gateway] = lambda: gateway
    app.dependency_overrides[get_agent_answer_gateway] = lambda: gateway
    return gateway


async def test_natural_language_action_creates_pending_dry_run_only(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    gateway = override_action_plan_gateway()
    response = await client.post(
        QUERY_URL,
        headers=admin_headers,
        json={"query": "Change our contact email to agent.operations@example.test"},
    )

    assert response.status_code == 200
    body = response.json()
    assert gateway.plan_call_count == 1
    assert gateway.answer_call_count == 0
    assert set(gateway.received_action_names) == EXPECTED_ACTION_NAMES
    assert body["mode"] == "action_proposal"
    assert body["answer_source"] == "deterministic"
    assert body["results"] == []
    assert body["evidence_ids"] == []
    proposal = body["action_proposal"]
    assert set(proposal) == {
        "id",
        "action_name",
        "risk_level",
        "status",
        "changes",
        "expires_at",
    }
    assert proposal["status"] == "pending_approval"
    assert proposal["changes"] == [
        {
            "field": "contact_email",
            "before": "operations@example.test",
            "after": "agent.operations@example.test",
        }
    ]

    organization = await db_session.get(OrganizationORM, ORGANIZATION_ID)
    assert organization is not None
    await db_session.refresh(organization)
    assert organization.contact_email == "operations@example.test"
    assert organization.version == 1

    stored_proposal = await db_session.get(AgentActionProposalORM, proposal["id"])
    assert stored_proposal is not None
    assert stored_proposal.status == "pending_approval"
    assert stored_proposal.organization_id == ORGANIZATION_ID
    assert stored_proposal.requested_by_user_id == "usr_admin_001"

    audit_result = await db_session.execute(
        select(AuditEventORM).where(
            AuditEventORM.organization_id == ORGANIZATION_ID,
            AuditEventORM.event_type == "agent_action_proposed",
        )
    )
    audit_event = audit_result.scalars().one()
    assert audit_event.details_json["proposal_source"] == "agent_query"
    assert audit_event.details_json["planner"] == "configured_model"
    assert audit_event.details_json["request_id"] == response.headers["X-Request-Id"]
    assert len(audit_event.details_json["request_hash"]) == 64
    assert "Change our contact email" not in str(audit_event.details_json)


async def test_natural_language_proposal_uses_existing_approval_execution_flow(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    override_action_plan_gateway()
    proposal_response = await client.post(
        QUERY_URL,
        headers=admin_headers,
        json={"query": "Change our contact email"},
    )
    proposal_id = proposal_response.json()["action_proposal"]["id"]

    approval_response = await client.post(
        f"{ACTION_BASE_URL}/{proposal_id}/approve",
        headers=admin_headers,
        json={"reason": "Approved after reviewing the dry-run"},
    )
    assert approval_response.status_code == 200

    execution_response = await client.post(
        f"{ACTION_BASE_URL}/{proposal_id}/execute",
        headers=admin_headers,
        json={"idempotency_key": "agent-query-contact-email-001"},
    )
    assert execution_response.status_code == 200
    assert execution_response.json()["execution"]["outcome"] == "succeeded"

    organization = await db_session.get(OrganizationORM, ORGANIZATION_ID)
    assert organization is not None
    await db_session.refresh(organization)
    assert organization.contact_email == "agent.operations@example.test"
    assert organization.version == 2


async def test_reader_cannot_create_natural_language_admin_proposal(
    client: AsyncClient,
    db_session: AsyncSession,
    reader_headers: dict[str, str],
) -> None:
    gateway = override_action_plan_gateway()
    response = await client.post(
        QUERY_URL,
        headers=reader_headers,
        json={"query": "Change the contact email"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"
    assert gateway.plan_call_count == 1
    proposal_count = await db_session.scalar(select(AgentActionProposalORM.id).limit(1))
    assert proposal_count is None


async def test_provider_failure_creates_no_action_proposal(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    response = await client.post(
        QUERY_URL,
        headers=admin_headers,
        json={"query": "Change the contact email"},
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "agent_model_unavailable"
    proposal = await db_session.scalar(select(AgentActionProposalORM.id).limit(1))
    assert proposal is None
