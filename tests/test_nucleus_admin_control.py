from __future__ import annotations

from datetime import datetime, timezone

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.nucleus_admin_models import NucleusActorMappingORM
from app.db.nucleus_models import NucleusOrganizationAccountORM
from app.db.orm_models import OrganizationOverviewORM, OrganizationSeatPoolORM

ORGANIZATION_ID = "org_sandbox_001"
BASE = f"/workplace/organizations/{ORGANIZATION_ID}/agent/actions"
APPROVER_ONE = {"X-Mock-User-Id": "usr_approval_admin_001"}
APPROVER_TWO = {"X-Mock-User-Id": "usr_approval_admin_002"}


async def _propose(
    client: AsyncClient,
    headers: dict[str, str],
    action_name: str,
    arguments: dict[str, str],
) -> dict:
    response = await client.post(
        f"{BASE}/propose",
        headers=headers,
        json={"action_name": action_name, "arguments": arguments},
    )
    assert response.status_code == 200, response.text
    return response.json()["proposal"]


async def _approve_high_risk(
    client: AsyncClient,
    proposal_id: str,
) -> None:
    first = await client.post(
        f"{BASE}/{proposal_id}/approve",
        headers=APPROVER_ONE,
        json={"reason": "Independent review one"},
    )
    assert first.status_code == 200, first.text
    second = await client.post(
        f"{BASE}/{proposal_id}/approve",
        headers=APPROVER_TWO,
        json={"reason": "Independent review two"},
    )
    assert second.status_code == 200, second.text


async def _execute(
    client: AsyncClient,
    headers: dict[str, str],
    proposal_id: str,
    key: str,
) -> dict:
    response = await client.post(
        f"{BASE}/{proposal_id}/execute",
        headers=headers,
        json={"idempotency_key": key},
    )
    assert response.status_code == 200, response.text
    return response.json()["execution"]


async def test_username_change_requires_two_approvals_and_records_executor(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    proposal = await _propose(
        client,
        admin_headers,
        "update_nucleus_organization_username",
        {"username": "internal.company.admin"},
    )
    assert proposal["approval_policy"] == {
        "self_approval_allowed": False,
        "required_approver_permission": (
            "organization.account.identity.update"
        ),
        "minimum_approvals": 2,
    }
    await _approve_high_risk(client, proposal["id"])
    execution = await _execute(
        client,
        admin_headers,
        proposal["id"],
        "username-admin-control-001",
    )
    assert execution["executed_by_user_id"] == "usr_admin_001"
    assert execution["nucleus_actor_id"] == 1001

    account = await db_session.get(NucleusOrganizationAccountORM, 1)
    assert account is not None
    await db_session.refresh(account)
    assert account.user_name == "internal.company.admin"
    assert account.updated_by == 1001
    assert account.password == "$mock$not-a-real-password"

    assert "password" not in str(execution).lower()


async def test_sensitive_execution_fails_closed_without_actor_mapping(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    proposal = await _propose(
        client,
        admin_headers,
        "update_nucleus_organization_username",
        {"username": "mapping.required"},
    )
    await _approve_high_risk(client, proposal["id"])
    mapping = await db_session.get(
        NucleusActorMappingORM, "usr_admin_001"
    )
    assert mapping is not None
    await db_session.delete(mapping)
    await db_session.commit()

    response = await client.post(
        f"{BASE}/{proposal['id']}/execute",
        headers=admin_headers,
        json={"idempotency_key": "missing-actor-mapping-001"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == (
        "agent_action_state_conflict"
    )


async def test_license_change_synchronizes_all_reviewed_resources(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    proposal = await _propose(
        client,
        admin_headers,
        "update_nucleus_organization_license",
        {
            "max_user_limit": "8",
            "license_start_date": "2026-01-01T00:00:00+00:00",
            "license_end_date": "2027-01-31T00:00:00+00:00",
        },
    )
    assert {
        item["resource_type"]
        for item in proposal["resource_preconditions"]
    } == {
        "OrganizationAccount",
        "organization_seat_pool",
        "organization_overview",
    }
    await _approve_high_risk(client, proposal["id"])
    await _execute(
        client,
        admin_headers,
        proposal["id"],
        "license-admin-control-001",
    )

    account = await db_session.get(NucleusOrganizationAccountORM, 1)
    pool = await db_session.get(
        OrganizationSeatPoolORM, "seatpool_sandbox_standard"
    )
    overview = await db_session.get(OrganizationOverviewORM, ORGANIZATION_ID)
    assert account is not None and pool is not None and overview is not None
    await db_session.refresh(account)
    await db_session.refresh(pool)
    await db_session.refresh(overview)
    assert account.max_user_limit == 8
    assert account.license_end_date.replace(tzinfo=timezone.utc) == datetime(
        2027, 1, 31, tzinfo=timezone.utc
    )
    assert pool.total_seats == 8
    assert pool.expires_at.replace(tzinfo=timezone.utc) == datetime(
        2027, 1, 31, tzinfo=timezone.utc
    )
    assert overview.renewal_date.isoformat() == "2027-01-31"


async def test_rejection_uses_backend_actor_and_suspends_projections(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    proposal = await _propose(
        client,
        admin_headers,
        "reject_nucleus_organization_account",
        {"reason": "Internal compliance hold"},
    )
    fields = {change["field"] for change in proposal["changes"]}
    assert {"RejectedBy", "RejectedDate", "organization.status"}.issubset(
        fields
    )
    await _approve_high_risk(client, proposal["id"])
    await _execute(
        client,
        admin_headers,
        proposal["id"],
        "reject-admin-control-001",
    )
    account = await db_session.get(NucleusOrganizationAccountORM, 1)
    assert account is not None
    await db_session.refresh(account)
    assert account.status == "rejected"
    assert account.is_active is False
    assert account.rejected_by == 1001
    assert account.rejection_reason == "Internal compliance hold"
