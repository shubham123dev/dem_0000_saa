from __future__ import annotations

from httpx import AsyncClient

from app.adapters.user.sandbox_adapter import get_sandbox_user_directory
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.orm_models import (
    OrganizationMembershipORM,
    OrganizationReportAccessORM,
    SeatAssignmentORM,
)
from app.domain.enums import UserStatus
from app.domain.models import User

ORGANIZATION_ID = "org_sandbox_001"
ACTION_BASE_URL = f"/workplace/organizations/{ORGANIZATION_ID}/agent/actions"


async def propose(
    client: AsyncClient,
    headers: dict[str, str],
    action_name: str,
    arguments: dict[str, str],
):
    return await client.post(
        f"{ACTION_BASE_URL}/propose",
        headers=headers,
        json={"action_name": action_name, "arguments": arguments},
    )


async def add_peer_admins(db_session: AsyncSession) -> tuple[dict[str, str], dict[str, str]]:
    for suffix in ("inverse_a", "inverse_b"):
        user_id = f"usr_{suffix}"
        get_sandbox_user_directory().upsert(
            User(
                id=user_id,
                display_name=suffix,
                email=f"{suffix}@example.test",
                status=UserStatus.ACTIVE,
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
        {"X-Mock-User-Id": "usr_inverse_a"},
        {"X-Mock-User-Id": "usr_inverse_b"},
    )


async def approve_execute(
    client: AsyncClient,
    headers: dict[str, str],
    proposal_id: str,
    key: str,
    *,
    approvers: tuple[dict[str, str], ...] | None = None,
):
    decision_headers = approvers or (headers,)
    for decision_header in decision_headers:
        approval = await client.post(
            f"{ACTION_BASE_URL}/{proposal_id}/approve",
            headers=decision_header,
            json={"reason": "Reviewed inverse lifecycle change"},
        )
        assert approval.status_code == 200
    return await client.post(
        f"{ACTION_BASE_URL}/{proposal_id}/execute",
        headers=headers,
        json={"idempotency_key": key},
    )


async def test_activate_invited_membership(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    response = await propose(
        client,
        admin_headers,
        "activate_organization_membership",
        {"user_id": "usr_invited_001"},
    )
    assert response.status_code == 200
    proposal = response.json()["proposal"]
    assert proposal["changes"] == [
        {"field": "membership_status", "before": "invited", "after": "active"}
    ]
    execution = await approve_execute(
        client,
        admin_headers,
        proposal["id"],
        "activate-invited-member-001",
    )
    assert execution.status_code == 200
    membership = await db_session.scalar(
        select(OrganizationMembershipORM).where(
            OrganizationMembershipORM.organization_id == ORGANIZATION_ID,
            OrganizationMembershipORM.user_id == "usr_invited_001",
        )
    )
    assert membership is not None
    await db_session.refresh(membership)
    assert membership.membership_status == "active"
    assert membership.version == 2
    assert membership.joined_at is not None


async def test_update_member_role_is_versioned(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    approvers = await add_peer_admins(db_session)
    response = await propose(
        client,
        admin_headers,
        "update_organization_member_role",
        {"user_id": "usr_member_003", "role": "sandbox_admin"},
    )
    assert response.status_code == 200
    proposal = response.json()["proposal"]
    execution = await approve_execute(
        client,
        admin_headers,
        proposal["id"],
        "promote-member-003-001",
        approvers=approvers,
    )
    assert execution.status_code == 200
    membership = await db_session.scalar(
        select(OrganizationMembershipORM).where(
            OrganizationMembershipORM.organization_id == ORGANIZATION_ID,
            OrganizationMembershipORM.user_id == "usr_member_003",
        )
    )
    assert membership is not None
    await db_session.refresh(membership)
    assert membership.role == "sandbox_admin"
    assert membership.version == 2


async def test_last_active_admin_cannot_be_demoted(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    await db_session.execute(
        update(OrganizationMembershipORM)
        .where(
            OrganizationMembershipORM.organization_id == ORGANIZATION_ID,
            OrganizationMembershipORM.user_id.in_(
                ("usr_approval_admin_001", "usr_approval_admin_002")
            ),
        )
        .values(membership_status="removed")
    )
    await db_session.commit()

    response = await propose(
        client,
        admin_headers,
        "update_organization_member_role",
        {"user_id": "usr_admin_001", "role": "sandbox_reader"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "agent_action_invalid"


async def test_remove_invited_member_preserves_history(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    approvers = await add_peer_admins(db_session)
    response = await propose(
        client,
        admin_headers,
        "remove_organization_user",
        {"user_id": "usr_invited_001"},
    )
    assert response.status_code == 200
    proposal = response.json()["proposal"]
    execution = await approve_execute(
        client,
        admin_headers,
        proposal["id"],
        "remove-invited-member-001",
        approvers=approvers,
    )
    assert execution.status_code == 200
    membership = await db_session.scalar(
        select(OrganizationMembershipORM).where(
            OrganizationMembershipORM.organization_id == ORGANIZATION_ID,
            OrganizationMembershipORM.user_id == "usr_invited_001",
        )
    )
    assert membership is not None
    await db_session.refresh(membership)
    assert membership.membership_status == "removed"
    assert membership.version == 2


async def test_member_with_active_seat_must_be_unseated_before_removal(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    response = await propose(
        client,
        admin_headers,
        "remove_organization_user",
        {"user_id": "usr_member_001"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "agent_action_invalid"


async def test_revoke_active_seat_preserves_assignment_record(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    response = await propose(
        client,
        admin_headers,
        "revoke_organization_seat",
        {"user_id": "usr_member_001", "seat_type": "standard"},
    )
    assert response.status_code == 200
    proposal = response.json()["proposal"]
    execution = await approve_execute(
        client,
        admin_headers,
        proposal["id"],
        "revoke-member-seat-001",
    )
    assert execution.status_code == 200
    assignment = await db_session.scalar(
        select(SeatAssignmentORM).where(
            SeatAssignmentORM.organization_id == ORGANIZATION_ID,
            SeatAssignmentORM.user_id == "usr_member_001",
        )
    )
    assert assignment is not None
    await db_session.refresh(assignment)
    assert assignment.status == "revoked"
    assert assignment.version == 2
    assert assignment.revoked_at is not None
    assert assignment.revoked_by_user_id == "usr_admin_001"


async def test_revoke_report_access_preserves_grant_record(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    response = await propose(
        client,
        admin_headers,
        "revoke_organization_report_access",
        {"report_id": "rpt_market_001"},
    )
    assert response.status_code == 200
    proposal = response.json()["proposal"]
    execution = await approve_execute(
        client,
        admin_headers,
        proposal["id"],
        "revoke-report-access-001",
    )
    assert execution.status_code == 200
    access = await db_session.scalar(
        select(OrganizationReportAccessORM).where(
            OrganizationReportAccessORM.organization_id == ORGANIZATION_ID,
            OrganizationReportAccessORM.report_id == "rpt_market_001",
        )
    )
    assert access is not None
    await db_session.refresh(access)
    assert access.status == "revoked"
    assert access.version == 2
