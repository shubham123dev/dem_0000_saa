from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.orm_models import (
    OrganizationMembershipORM,
    OrganizationReportAccessORM,
    SeatAssignmentORM,
)

ORGANIZATION_ID = "org_sandbox_001"
ACTION_BASE_URL = f"/workplace/organizations/{ORGANIZATION_ID}/agent/actions"
EXPECTED_ACTIONS = {
    "update_organization_contact_email",
    "update_nucleus_organization_account_field",
    "clear_nucleus_organization_account_field",
    "grant_nucleus_category_access",
    "revoke_nucleus_category_access",
    "grant_nucleus_report_access",
    "revoke_nucleus_report_access",
    "update_nucleus_organization_permissions",
    "update_nucleus_organization_username",
    "update_nucleus_organization_license",
    "approve_nucleus_organization_account",
    "reject_nucleus_organization_account",
    "activate_nucleus_organization_account",
    "deactivate_nucleus_organization_account",
    "grant_nucleus_company_profile_access",
    "revoke_nucleus_company_profile_access",
    "grant_nucleus_drug_access",
    "revoke_nucleus_drug_access",
    "grant_nucleus_indication_access",
    "revoke_nucleus_indication_access",
    "grant_nucleus_market_access",
    "revoke_nucleus_market_access",
    "invite_organization_user",
    "activate_organization_membership",
    "update_organization_member_role",
    "remove_organization_user",
    "assign_organization_seat",
    "revoke_organization_seat",
    "grant_organization_report_access",
    "revoke_organization_report_access",
    "create_workplace_resource",
    "update_workplace_resource",
    "clear_workplace_resource_fields",
    "activate_workplace_resource",
    "deactivate_workplace_resource",
    "delete_workplace_resource",
    "restore_workplace_resource",
    "bulk_update_workplace_resources",
}


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


async def approve_and_execute(
    client: AsyncClient,
    headers: dict[str, str],
    proposal_id: str,
    idempotency_key: str,
):
    approval = await client.post(
        f"{ACTION_BASE_URL}/{proposal_id}/approve",
        headers=headers,
        json={"reason": "Approved after reviewing the dry-run"},
    )
    assert approval.status_code == 200
    execution = await client.post(
        f"{ACTION_BASE_URL}/{proposal_id}/execute",
        headers=headers,
        json={"idempotency_key": idempotency_key},
    )
    assert execution.status_code == 200
    return execution.json()["execution"]


async def test_capabilities_advertise_registry_backed_actions(client: AsyncClient) -> None:
    response = await client.get("/workplace/capabilities")
    assert response.status_code == 200
    actions = {item["name"]: item for item in response.json()["write_actions"]}
    assert set(actions) == EXPECTED_ACTIONS
    assert all(item["requires_approval"] for item in actions.values())
    assert all(item["supports_dry_run"] for item in actions.values())


async def test_invite_user_is_dry_run_then_persists_invited_membership(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    response = await propose(
        client,
        admin_headers,
        "invite_organization_user",
        {
            "email": "outsider@example.test",
            "display_name": "Outsider User",
            "role": "sandbox_reader",
        },
    )
    assert response.status_code == 200
    proposal = response.json()["proposal"]
    assert proposal["status"] == "pending_approval"
    assert proposal["changes"][0]["before"] is None

    before = await db_session.scalar(
        select(OrganizationMembershipORM).where(
            OrganizationMembershipORM.organization_id == ORGANIZATION_ID,
            OrganizationMembershipORM.user_id == "usr_outsider_001",
        )
    )
    assert before is None

    execution = await approve_and_execute(
        client,
        admin_headers,
        proposal["id"],
        "invite-outsider-user-001",
    )
    assert execution["outcome"] == "succeeded"

    membership = await db_session.scalar(
        select(OrganizationMembershipORM).where(
            OrganizationMembershipORM.organization_id == ORGANIZATION_ID,
            OrganizationMembershipORM.user_id == "usr_outsider_001",
        )
    )
    assert membership is not None
    await db_session.refresh(membership)
    assert membership.membership_status == "invited"
    assert membership.role == "sandbox_reader"
    assert membership.version == 1


async def test_assign_seat_uses_available_capacity_and_active_membership(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    response = await propose(
        client,
        admin_headers,
        "assign_organization_seat",
        {"user_id": "usr_member_003", "seat_type": "standard"},
    )
    assert response.status_code == 200
    proposal = response.json()["proposal"]
    assert proposal["changes"] == [
        {"field": "active_seat", "before": False, "after": True}
    ]

    execution = await approve_and_execute(
        client,
        admin_headers,
        proposal["id"],
        "assign-member-seat-001",
    )
    assert execution["outcome"] == "succeeded"

    assignment = await db_session.scalar(
        select(SeatAssignmentORM).where(
            SeatAssignmentORM.organization_id == ORGANIZATION_ID,
            SeatAssignmentORM.user_id == "usr_member_003",
            SeatAssignmentORM.status == "active",
        )
    )
    assert assignment is not None


async def test_grant_report_access_creates_versioned_active_grant(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    response = await propose(
        client,
        admin_headers,
        "grant_organization_report_access",
        {"report_id": "rpt_market_004", "access_level": "download"},
    )
    assert response.status_code == 200
    proposal = response.json()["proposal"]
    assert proposal["changes"][0]["after"] == {
        "access_level": "download",
        "status": "active",
    }

    execution = await approve_and_execute(
        client,
        admin_headers,
        proposal["id"],
        "grant-report-access-001",
    )
    assert execution["outcome"] == "succeeded"

    access = await db_session.scalar(
        select(OrganizationReportAccessORM).where(
            OrganizationReportAccessORM.organization_id == ORGANIZATION_ID,
            OrganizationReportAccessORM.report_id == "rpt_market_004",
        )
    )
    assert access is not None
    await db_session.refresh(access)
    assert access.access_level == "download"
    assert access.status == "active"
    assert access.version == 1


async def test_reader_cannot_propose_operational_actions(
    client: AsyncClient,
    reader_headers: dict[str, str],
) -> None:
    response = await propose(
        client,
        reader_headers,
        "assign_organization_seat",
        {"user_id": "usr_member_003", "seat_type": "standard"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"


async def test_operational_action_rejects_extra_identity_arguments(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    response = await propose(
        client,
        admin_headers,
        "grant_organization_report_access",
        {
            "report_id": "rpt_market_004",
            "access_level": "view",
            "organization_id": "org_other_001",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "agent_action_invalid"
