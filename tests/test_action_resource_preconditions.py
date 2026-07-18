from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.action_models import AgentActionProposalORM

ORGANIZATION_ID = "org_sandbox_001"
ACTION_BASE = f"/workplace/organizations/{ORGANIZATION_ID}/agent/actions"


async def test_single_resource_action_persists_one_precondition(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    response = await client.post(
        f"{ACTION_BASE}/propose",
        headers=admin_headers,
        json={
            "action_name": "clear_nucleus_organization_account_field",
            "arguments": {"field_name": "Website"},
        },
    )
    assert response.status_code == 200
    proposal = response.json()["proposal"]
    assert proposal["fingerprint_version"] == 3
    assert proposal["resource_preconditions"] == [
        {
            "resource_type": "OrganizationAccount",
            "resource_id": "1",
            "observed_version": 1,
        }
    ]


async def test_contact_email_action_persists_both_reviewed_resources(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    response = await client.post(
        f"{ACTION_BASE}/propose",
        headers=admin_headers,
        json={
            "action_name": "update_organization_contact_email",
            "arguments": {"contact_email": "two-resource@example.test"},
        },
    )
    assert response.status_code == 200
    proposal = response.json()["proposal"]
    assert proposal["fingerprint_version"] == 3
    assert {
        (item["resource_type"], item["resource_id"])
        for item in proposal["resource_preconditions"]
    } == {
        ("OrganizationAccount", "1"),
        ("organization", ORGANIZATION_ID),
    }


async def test_tampered_resource_precondition_invalidates_fingerprint(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    response = await client.post(
        f"{ACTION_BASE}/propose",
        headers=admin_headers,
        json={
            "action_name": "update_organization_contact_email",
            "arguments": {"contact_email": "precondition@example.test"},
        },
    )
    proposal_id = response.json()["proposal"]["id"]
    approved = await client.post(
        f"{ACTION_BASE}/{proposal_id}/approve",
        headers=admin_headers,
        json={"reason": "Reviewed"},
    )
    assert approved.status_code == 200

    row = await db_session.get(AgentActionProposalORM, proposal_id)
    assert row is not None
    tampered = list(row.resource_preconditions_json)
    tampered[0] = {**tampered[0], "observed_version": 999}
    row.resource_preconditions_json = tampered
    await db_session.commit()

    executed = await client.post(
        f"{ACTION_BASE}/{proposal_id}/execute",
        headers=admin_headers,
        json={"idempotency_key": "tampered-precondition-001"},
    )
    assert executed.status_code == 409
    assert executed.json()["error"]["code"] == "agent_action_state_conflict"
