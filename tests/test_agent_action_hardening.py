from __future__ import annotations

import asyncio

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.orm_models import OrganizationORM

ORGANIZATION_ID = "org_sandbox_001"
ACTION_BASE_URL = f"/workplace/organizations/{ORGANIZATION_ID}/agent/actions"


async def propose(client: AsyncClient, headers: dict[str, str], email: str):
    return await client.post(
        f"{ACTION_BASE_URL}/propose",
        headers=headers,
        json={
            "action_name": "update_organization_contact_email",
            "contact_email": email,
        },
    )


async def test_cancelled_proposal_is_listed_and_cannot_execute(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    proposal_response = await propose(
        client,
        admin_headers,
        "cancelled@example.test",
    )
    proposal_id = proposal_response.json()["proposal"]["id"]
    cancel_response = await client.post(
        f"{ACTION_BASE_URL}/{proposal_id}/cancel",
        headers=admin_headers,
        json={"reason": "No longer needed"},
    )
    assert cancel_response.status_code == 200
    assert cancel_response.json()["proposal"]["status"] == "cancelled"
    assert cancel_response.json()["proposal"]["cancelled_at"] is not None

    listed = await client.get(
        ACTION_BASE_URL,
        headers=admin_headers,
        params={"status": "cancelled"},
    )
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["proposals"]] == [proposal_id]

    execute_response = await client.post(
        f"{ACTION_BASE_URL}/{proposal_id}/execute",
        headers=admin_headers,
        json={"idempotency_key": "cancelled-execution-key"},
    )
    assert execute_response.status_code == 409
    assert execute_response.json()["error"]["code"] == "agent_action_cancelled"


async def test_resource_change_marks_approved_proposal_stale(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    proposal_response = await propose(
        client,
        admin_headers,
        "proposed@example.test",
    )
    proposal_id = proposal_response.json()["proposal"]["id"]
    approval_response = await client.post(
        f"{ACTION_BASE_URL}/{proposal_id}/approve",
        headers=admin_headers,
        json={"reason": "Approved"},
    )
    assert approval_response.status_code == 200

    organization = await db_session.get(OrganizationORM, ORGANIZATION_ID)
    assert organization is not None
    organization.contact_email = "changed-before-execution@example.test"
    organization.version += 1
    await db_session.commit()

    execution_response = await client.post(
        f"{ACTION_BASE_URL}/{proposal_id}/execute",
        headers=admin_headers,
        json={"idempotency_key": "stale-execution-key"},
    )
    assert execution_response.status_code == 409
    assert execution_response.json()["error"]["code"] == "agent_action_stale"

    proposal_response = await client.get(
        f"{ACTION_BASE_URL}/{proposal_id}",
        headers=admin_headers,
    )
    assert proposal_response.json()["proposal"]["status"] == "stale"
    assert proposal_response.json()["proposal"]["stale_at"] is not None


async def test_only_one_concurrent_approval_decision_succeeds(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    proposal_response = await propose(
        client,
        admin_headers,
        "concurrent@example.test",
    )
    proposal_id = proposal_response.json()["proposal"]["id"]

    responses = await asyncio.gather(
        client.post(
            f"{ACTION_BASE_URL}/{proposal_id}/approve",
            headers=admin_headers,
            json={"reason": "Approve"},
        ),
        client.post(
            f"{ACTION_BASE_URL}/{proposal_id}/reject",
            headers=admin_headers,
            json={"reason": "Reject"},
        ),
    )
    assert sorted(response.status_code for response in responses) == [200, 409]
    conflict = next(response for response in responses if response.status_code == 409)
    assert conflict.json()["error"]["code"] == "agent_action_already_decided"
