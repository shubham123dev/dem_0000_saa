from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.action_models import AgentActionApprovalORM, AgentActionRollbackORM
from app.db.orm_models import OrganizationMembershipORM, OrganizationORM, UserORM

ORGANIZATION_ID = "org_sandbox_001"
ACTION_BASE_URL = f"/workplace/organizations/{ORGANIZATION_ID}/agent/actions"


async def add_peer_admins(db_session: AsyncSession) -> tuple[dict[str, str], dict[str, str]]:
    for suffix in ("a", "b"):
        user_id = f"usr_approver_{suffix}"
        db_session.add(
            UserORM(
                id=user_id,
                display_name=f"Approver {suffix.upper()}",
                email=f"approver.{suffix}@example.test",
                status="active",
            )
        )
        db_session.add(
            OrganizationMembershipORM(
                organization_id=ORGANIZATION_ID,
                user_id=user_id,
                role="sandbox_admin",
                membership_status="active",
                version=1,
            )
        )
    await db_session.commit()
    return (
        {"X-Mock-User-Id": "usr_approver_a"},
        {"X-Mock-User-Id": "usr_approver_b"},
    )


async def test_high_risk_action_requires_two_distinct_non_requester_approvals(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    approver_a, approver_b = await add_peer_admins(db_session)
    proposed = await client.post(
        f"{ACTION_BASE_URL}/propose",
        headers=admin_headers,
        json={
            "action_name": "update_organization_member_role",
            "arguments": {
                "user_id": "usr_member_003",
                "role": "sandbox_admin",
            },
        },
    )
    assert proposed.status_code == 200
    proposal = proposed.json()["proposal"]
    assert proposal["approval_policy"] == {
        "self_approval_allowed": False,
        "required_approver_permission": "organization.users.update",
        "minimum_approvals": 2,
    }

    self_approval = await client.post(
        f"{ACTION_BASE_URL}/{proposal['id']}/approve",
        headers=admin_headers,
        json={"reason": "Requester must not approve"},
    )
    assert self_approval.status_code == 409

    first = await client.post(
        f"{ACTION_BASE_URL}/{proposal['id']}/approve",
        headers=approver_a,
        json={"reason": "First independent review"},
    )
    assert first.status_code == 200
    after_first = await client.get(
        f"{ACTION_BASE_URL}/{proposal['id']}",
        headers=approver_a,
    )
    assert after_first.json()["proposal"]["status"] == "pending_approval"

    duplicate = await client.post(
        f"{ACTION_BASE_URL}/{proposal['id']}/approve",
        headers=approver_a,
        json={"reason": "Duplicate review"},
    )
    assert duplicate.status_code == 409

    premature = await client.post(
        f"{ACTION_BASE_URL}/{proposal['id']}/execute",
        headers=admin_headers,
        json={"idempotency_key": "high-risk-before-threshold"},
    )
    assert premature.status_code == 409

    second = await client.post(
        f"{ACTION_BASE_URL}/{proposal['id']}/approve",
        headers=approver_b,
        json={"reason": "Second independent review"},
    )
    assert second.status_code == 200
    approved = await client.get(
        f"{ACTION_BASE_URL}/{proposal['id']}",
        headers=approver_b,
    )
    assert approved.json()["proposal"]["status"] == "approved"

    executed = await client.post(
        f"{ACTION_BASE_URL}/{proposal['id']}/execute",
        headers=admin_headers,
        json={"idempotency_key": "high-risk-after-threshold"},
    )
    assert executed.status_code == 200
    assert executed.json()["execution"]["outcome"] == "succeeded"

    membership = await db_session.scalar(
        select(OrganizationMembershipORM).where(
            OrganizationMembershipORM.organization_id == ORGANIZATION_ID,
            OrganizationMembershipORM.user_id == "usr_member_003",
        )
    )
    assert membership is not None
    await db_session.refresh(membership)
    assert membership.role == "sandbox_admin"

    approvals = (
        await db_session.execute(
            select(AgentActionApprovalORM).where(
                AgentActionApprovalORM.proposal_id == proposal["id"]
            )
        )
    ).scalars().all()
    assert len(approvals) == 2
    assert {item.decided_by_user_id for item in approvals} == {
        "usr_approver_a",
        "usr_approver_b",
    }
    assert all(item.consumed_at is not None for item in approvals)


async def test_successful_contact_change_creates_separate_rollback_proposal(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    proposed = await client.post(
        f"{ACTION_BASE_URL}/propose",
        headers=admin_headers,
        json={
            "action_name": "update_organization_contact_email",
            "arguments": {"contact_email": "changed@example.test"},
        },
    )
    source = proposed.json()["proposal"]
    assert (
        await client.post(
            f"{ACTION_BASE_URL}/{source['id']}/approve",
            headers=admin_headers,
            json={"reason": "Reviewed"},
        )
    ).status_code == 200
    assert (
        await client.post(
            f"{ACTION_BASE_URL}/{source['id']}/execute",
            headers=admin_headers,
            json={"idempotency_key": "contact-change-source"},
        )
    ).status_code == 200

    rollback_response = await client.post(
        f"{ACTION_BASE_URL}/{source['id']}/rollback-proposal",
        headers=admin_headers,
        json={"reason": "Restore prior contact"},
    )
    assert rollback_response.status_code == 200
    rollback = rollback_response.json()["proposal"]
    assert rollback["action_name"] == "update_organization_contact_email"
    assert rollback["status"] == "pending_approval"
    assert rollback["changes"] == [
        {
            "field": "contact_email",
            "before": "changed@example.test",
            "after": "operations@example.test",
        }
    ]

    organization = await db_session.get(OrganizationORM, ORGANIZATION_ID)
    assert organization is not None
    await db_session.refresh(organization)
    assert organization.contact_email == "changed@example.test"

    lineage = await db_session.scalar(
        select(AgentActionRollbackORM).where(
            AgentActionRollbackORM.source_proposal_id == source["id"],
            AgentActionRollbackORM.rollback_proposal_id == rollback["id"],
        )
    )
    assert lineage is not None

    assert (
        await client.post(
            f"{ACTION_BASE_URL}/{rollback['id']}/approve",
            headers=admin_headers,
            json={"reason": "Approve restoration"},
        )
    ).status_code == 200
    restored = await client.post(
        f"{ACTION_BASE_URL}/{rollback['id']}/execute",
        headers=admin_headers,
        json={"idempotency_key": "contact-change-rollback"},
    )
    assert restored.status_code == 200
    await db_session.refresh(organization)
    assert organization.contact_email == "operations@example.test"
