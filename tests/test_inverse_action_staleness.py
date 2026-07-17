from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.action_models import AgentActionProposalORM
from app.db.orm_models import OrganizationMembershipORM

ORGANIZATION_ID = "org_sandbox_001"
ACTION_BASE_URL = f"/workplace/organizations/{ORGANIZATION_ID}/agent/actions"


async def test_approved_membership_action_becomes_stale_after_resource_drift(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    proposal_response = await client.post(
        f"{ACTION_BASE_URL}/propose",
        headers=admin_headers,
        json={
            "action_name": "activate_organization_membership",
            "arguments": {"user_id": "usr_invited_001"},
        },
    )
    assert proposal_response.status_code == 200
    proposal_id = proposal_response.json()["proposal"]["id"]

    approval = await client.post(
        f"{ACTION_BASE_URL}/{proposal_id}/approve",
        headers=admin_headers,
        json={"reason": "Approved before concurrent change"},
    )
    assert approval.status_code == 200

    membership = await db_session.scalar(
        select(OrganizationMembershipORM).where(
            OrganizationMembershipORM.organization_id == ORGANIZATION_ID,
            OrganizationMembershipORM.user_id == "usr_invited_001",
        )
    )
    assert membership is not None
    membership.membership_status = "active"
    membership.version += 1
    await db_session.commit()

    execution = await client.post(
        f"{ACTION_BASE_URL}/{proposal_id}/execute",
        headers=admin_headers,
        json={"idempotency_key": "stale-membership-activation-001"},
    )
    assert execution.status_code == 409
    assert execution.json()["error"]["code"] == "agent_action_stale"

    proposal = await db_session.get(AgentActionProposalORM, proposal_id)
    assert proposal is not None
    await db_session.refresh(proposal)
    assert proposal.status == "stale"
    assert proposal.stale_at is not None
