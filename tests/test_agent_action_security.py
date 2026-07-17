from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.action_registry import build_action_fingerprint
from app.db.action_models import AgentActionProposalORM
from app.db.orm_models import OrganizationORM

ORGANIZATION_ID = "org_sandbox_001"
ACTION_BASE_URL = f"/workplace/organizations/{ORGANIZATION_ID}/agent/actions"


def test_action_fingerprint_changes_with_immutable_scope() -> None:
    baseline = build_action_fingerprint(
        organization_id="org_001",
        requested_by_user_id="usr_001",
        action_name="update_organization_contact_email",
        arguments={"contact_email": "one@example.test"},
        resource_type="organization",
        resource_id="org_001",
    )
    variants = {
        build_action_fingerprint(
            organization_id="org_002",
            requested_by_user_id="usr_001",
            action_name="update_organization_contact_email",
            arguments={"contact_email": "one@example.test"},
            resource_type="organization",
            resource_id="org_001",
        ),
        build_action_fingerprint(
            organization_id="org_001",
            requested_by_user_id="usr_002",
            action_name="update_organization_contact_email",
            arguments={"contact_email": "one@example.test"},
            resource_type="organization",
            resource_id="org_001",
        ),
        build_action_fingerprint(
            organization_id="org_001",
            requested_by_user_id="usr_001",
            action_name="update_organization_contact_email",
            arguments={"contact_email": "two@example.test"},
            resource_type="organization",
            resource_id="org_001",
        ),
        build_action_fingerprint(
            organization_id="org_001",
            requested_by_user_id="usr_001",
            action_name="update_organization_contact_email",
            arguments={"contact_email": "one@example.test"},
            resource_type="organization",
            resource_id="org_002",
        ),
    }

    assert baseline not in variants
    assert len(variants) == 4


async def test_modified_approved_proposal_cannot_execute(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    proposal_response = await client.post(
        f"{ACTION_BASE_URL}/propose",
        headers=admin_headers,
        json={
            "action_name": "update_organization_contact_email",
            "contact_email": "approved@example.test",
        },
    )
    proposal_id = proposal_response.json()["proposal"]["id"]
    approval_response = await client.post(
        f"{ACTION_BASE_URL}/{proposal_id}/approve",
        headers=admin_headers,
        json={"reason": "Approved original value"},
    )
    assert approval_response.status_code == 200

    proposal_row = await db_session.get(AgentActionProposalORM, proposal_id)
    assert proposal_row is not None
    proposal_row.arguments_json = {"contact_email": "tampered@example.test"}
    await db_session.commit()

    execution_response = await client.post(
        f"{ACTION_BASE_URL}/{proposal_id}/execute",
        headers=admin_headers,
        json={"idempotency_key": "tampered-execution-001"},
    )

    assert execution_response.status_code == 409
    assert execution_response.json()["error"]["code"] == "agent_action_state_conflict"
    organization = await db_session.get(OrganizationORM, ORGANIZATION_ID)
    assert organization is not None
    await db_session.refresh(organization)
    assert organization.contact_email == "operations@example.test"
    assert organization.version == 1
