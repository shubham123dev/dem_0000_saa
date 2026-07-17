from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.orm_models import AuditEventORM, OrganizationORM

ORGANIZATION_ID = "org_sandbox_001"
ACTION_BASE_URL = f"/workplace/organizations/{ORGANIZATION_ID}/agent/actions"


async def _propose(
    client: AsyncClient,
    headers: dict[str, str],
    contact_email: str = "new.operations@example.test",
):
    return await client.post(
        f"{ACTION_BASE_URL}/propose",
        headers=headers,
        json={
            "action_name": "update_organization_contact_email",
            "contact_email": contact_email,
        },
    )


async def test_proposal_is_dry_run_and_does_not_mutate(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    response = await _propose(client, admin_headers)

    assert response.status_code == 200
    proposal = response.json()["proposal"]
    assert proposal["status"] == "pending_approval"
    assert proposal["risk_level"] == "low"
    assert proposal["changes"] == [
        {
            "field": "contact_email",
            "before": "operations@example.test",
            "after": "new.operations@example.test",
        }
    ]
    assert response.json()["requires_approval"] is True
    assert response.json()["dry_run"] is True

    organization = await db_session.get(OrganizationORM, ORGANIZATION_ID)
    assert organization is not None
    await db_session.refresh(organization)
    assert organization.contact_email == "operations@example.test"
    assert organization.version == 1


async def test_reader_cannot_propose_action(
    client: AsyncClient,
    reader_headers: dict[str, str],
) -> None:
    response = await _propose(client, reader_headers)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"


async def test_execution_requires_explicit_approval(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    proposal_response = await _propose(client, admin_headers)
    proposal_id = proposal_response.json()["proposal"]["id"]

    execution_response = await client.post(
        f"{ACTION_BASE_URL}/{proposal_id}/execute",
        headers=admin_headers,
        json={"idempotency_key": "execution-without-approval"},
    )

    assert execution_response.status_code == 409
    assert execution_response.json()["error"]["code"] == "agent_action_state_conflict"


async def test_rejected_action_cannot_execute(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    proposal_response = await _propose(client, admin_headers)
    proposal_id = proposal_response.json()["proposal"]["id"]

    rejection_response = await client.post(
        f"{ACTION_BASE_URL}/{proposal_id}/reject",
        headers=admin_headers,
        json={"reason": "Not required"},
    )
    assert rejection_response.status_code == 200
    assert rejection_response.json()["approval"]["decision"] == "rejected"

    execution_response = await client.post(
        f"{ACTION_BASE_URL}/{proposal_id}/execute",
        headers=admin_headers,
        json={"idempotency_key": "rejected-action-execution"},
    )
    assert execution_response.status_code == 409
    assert execution_response.json()["error"]["code"] == "agent_action_state_conflict"


async def test_approved_action_executes_idempotently_and_is_audited(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    proposal_response = await _propose(client, admin_headers)
    proposal_id = proposal_response.json()["proposal"]["id"]

    approval_response = await client.post(
        f"{ACTION_BASE_URL}/{proposal_id}/approve",
        headers=admin_headers,
        json={"reason": "Approved for sandbox verification"},
    )
    assert approval_response.status_code == 200
    assert approval_response.json()["approval"]["decision"] == "approved"

    execution_response = await client.post(
        f"{ACTION_BASE_URL}/{proposal_id}/execute",
        headers=admin_headers,
        json={"idempotency_key": "contact-email-change-001"},
    )
    assert execution_response.status_code == 200
    execution = execution_response.json()["execution"]
    assert execution["outcome"] == "succeeded"
    assert execution["result"] == {
        "organization_id": ORGANIZATION_ID,
        "contact_email": "new.operations@example.test",
        "version": 2,
    }

    organization = await db_session.get(OrganizationORM, ORGANIZATION_ID)
    assert organization is not None
    await db_session.refresh(organization)
    assert organization.contact_email == "new.operations@example.test"
    assert organization.version == 2

    repeated_response = await client.post(
        f"{ACTION_BASE_URL}/{proposal_id}/execute",
        headers=admin_headers,
        json={"idempotency_key": "contact-email-change-001"},
    )
    assert repeated_response.status_code == 200
    assert repeated_response.json()["execution"] == execution

    conflicting_response = await client.post(
        f"{ACTION_BASE_URL}/{proposal_id}/execute",
        headers=admin_headers,
        json={"idempotency_key": "contact-email-change-002"},
    )
    assert conflicting_response.status_code == 409
    assert conflicting_response.json()["error"]["code"] == "agent_action_state_conflict"

    audit_result = await db_session.execute(
        select(AuditEventORM).where(
            AuditEventORM.organization_id == ORGANIZATION_ID
        )
    )
    event_types = {
        event.event_type
        for event in audit_result.scalars().all()
        if event.details_json and event.details_json.get("proposal_id") == proposal_id
    }
    assert {
        "agent_action_proposed",
        "agent_action_approved",
        "agent_action_execution_started",
        "agent_action_succeeded",
    }.issubset(event_types)


async def test_action_request_rejects_identity_and_unknown_fields(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    response = await client.post(
        f"{ACTION_BASE_URL}/propose",
        headers=admin_headers,
        json={
            "action_name": "update_organization_contact_email",
            "contact_email": "new.operations@example.test",
            "organization_id": "org_other_001",
            "approved": True,
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["message"] == "Request validation failed."
