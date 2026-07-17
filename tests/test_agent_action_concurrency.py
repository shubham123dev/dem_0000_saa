from __future__ import annotations

import asyncio

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.action_models import AgentActionExecutionORM
from app.db.orm_models import OrganizationORM

ORGANIZATION_ID = "org_sandbox_001"
ACTION_BASE_URL = f"/workplace/organizations/{ORGANIZATION_ID}/agent/actions"


async def test_concurrent_execution_consumes_one_approval_and_mutates_once(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    proposal_response = await client.post(
        f"{ACTION_BASE_URL}/propose",
        headers=admin_headers,
        json={
            "action_name": "update_organization_contact_email",
            "contact_email": "atomic@example.test",
        },
    )
    proposal_id = proposal_response.json()["proposal"]["id"]
    approval_response = await client.post(
        f"{ACTION_BASE_URL}/{proposal_id}/approve",
        headers=admin_headers,
        json={"reason": "Approved"},
    )
    assert approval_response.status_code == 200

    responses = await asyncio.gather(
        client.post(
            f"{ACTION_BASE_URL}/{proposal_id}/execute",
            headers=admin_headers,
            json={"idempotency_key": "atomic-execution-key"},
        ),
        client.post(
            f"{ACTION_BASE_URL}/{proposal_id}/execute",
            headers=admin_headers,
            json={"idempotency_key": "atomic-execution-key"},
        ),
    )
    assert 200 in {response.status_code for response in responses}
    assert all(response.status_code in {200, 409} for response in responses)
    for response in responses:
        if response.status_code == 409:
            assert response.json()["error"]["code"] == "agent_action_execution_in_progress"

    organization = await db_session.get(OrganizationORM, ORGANIZATION_ID)
    assert organization is not None
    await db_session.refresh(organization)
    assert organization.contact_email == "atomic@example.test"
    assert organization.version == 2
    execution_count = await db_session.scalar(
        select(func.count())
        .select_from(AgentActionExecutionORM)
        .where(AgentActionExecutionORM.proposal_id == proposal_id)
    )
    assert execution_count == 1
