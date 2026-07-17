from __future__ import annotations

from datetime import datetime, timedelta, timezone

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.orm_models import OrganizationSeatPoolORM, SeatAssignmentORM

USERS_URL = "/workplace/organizations/org_sandbox_001/users"
SEATS_URL = "/workplace/organizations/org_sandbox_001/seats"

EXPECTED_MEMBER_IDS = {
    "usr_admin_001",
    "usr_approval_admin_001",
    "usr_approval_admin_002",
    "usr_member_001",
    "usr_member_002",
    "usr_member_003",
    "usr_invited_001",
}


async def test_list_users_returns_all_memberships(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    response = await client.get(USERS_URL, headers=admin_headers)
    assert response.status_code == 200
    response_body = response.json()
    assert response_body["access"]["permission"] == "organization.users.read"

    organization_members = response_body["members"]
    assert len(organization_members) == 7
    organization_member_by_user_id = {
        organization_member["user_id"]: organization_member
        for organization_member in organization_members
    }
    assert set(organization_member_by_user_id) == EXPECTED_MEMBER_IDS


async def test_users_and_seats_are_distinct(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    response_body = (await client.get(USERS_URL, headers=admin_headers)).json()
    organization_member_by_user_id = {
        organization_member["user_id"]: organization_member
        for organization_member in response_body["members"]
    }

    assert organization_member_by_user_id["usr_admin_001"]["has_active_seat"] is True
    assert (
        organization_member_by_user_id["usr_approval_admin_001"]["has_active_seat"]
        is False
    )
    assert (
        organization_member_by_user_id["usr_approval_admin_002"]["has_active_seat"]
        is False
    )
    assert organization_member_by_user_id["usr_member_001"]["has_active_seat"] is True
    assert organization_member_by_user_id["usr_member_002"]["has_active_seat"] is True
    assert organization_member_by_user_id["usr_member_003"]["has_active_seat"] is False
    assert (
        organization_member_by_user_id["usr_invited_001"]["membership_status"]
        == "invited"
    )
    assert (
        organization_member_by_user_id["usr_invited_001"]["has_active_seat"]
        is False
    )


async def test_seat_summary_is_computed(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    response = await client.get(SEATS_URL, headers=admin_headers)
    assert response.status_code == 200
    seat_summary = response.json()["seats"]
    assert seat_summary["seat_type"] == "standard"
    assert seat_summary["total_seats"] == 5
    assert seat_summary["active_assignments"] == 3
    assert seat_summary["available_seats"] == 2
    assert sorted(seat_summary["seated_user_ids"]) == [
        "usr_admin_001",
        "usr_member_001",
        "usr_member_002",
    ]


async def test_suspended_seat_pool_returns_zero_entitlement(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    seat_pool = await db_session.get(
        OrganizationSeatPoolORM,
        "seatpool_sandbox_standard",
    )
    assert seat_pool is not None
    seat_pool.status = "suspended"
    await db_session.commit()

    response = await client.get(SEATS_URL, headers=admin_headers)
    assert response.status_code == 200
    seat_summary = response.json()["seats"]
    assert seat_summary["total_seats"] == 0
    assert seat_summary["active_assignments"] == 0
    assert seat_summary["available_seats"] == 0
    assert seat_summary["seated_user_ids"] == []


async def test_expired_seat_pool_returns_zero_entitlement(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    seat_pool = await db_session.get(
        OrganizationSeatPoolORM,
        "seatpool_sandbox_standard",
    )
    assert seat_pool is not None
    seat_pool.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    await db_session.commit()

    response = await client.get(SEATS_URL, headers=admin_headers)
    assert response.status_code == 200
    seat_summary = response.json()["seats"]
    assert seat_summary["total_seats"] == 0
    assert seat_summary["active_assignments"] == 0
    assert seat_summary["available_seats"] == 0


async def test_future_seat_pool_returns_zero_entitlement(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    seat_pool = await db_session.get(
        OrganizationSeatPoolORM,
        "seatpool_sandbox_standard",
    )
    assert seat_pool is not None
    seat_pool.starts_at = datetime.now(timezone.utc) + timedelta(days=1)
    await db_session.commit()

    response = await client.get(SEATS_URL, headers=admin_headers)
    assert response.status_code == 200
    seat_summary = response.json()["seats"]
    assert seat_summary["total_seats"] == 0
    assert seat_summary["active_assignments"] == 0
    assert seat_summary["available_seats"] == 0


async def test_available_seats_never_becomes_negative(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    seat_pool = await db_session.get(
        OrganizationSeatPoolORM,
        "seatpool_sandbox_standard",
    )
    assert seat_pool is not None
    seat_pool.total_seats = 1
    await db_session.commit()

    response = await client.get(SEATS_URL, headers=admin_headers)
    assert response.status_code == 200
    seat_summary = response.json()["seats"]
    assert seat_summary["total_seats"] == 1
    assert seat_summary["active_assignments"] == 3
    assert seat_summary["available_seats"] == 0


async def test_invited_membership_seat_assignment_is_not_counted(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    db_session.add(
        SeatAssignmentORM(
            id="seat_invited_001",
            organization_id="org_sandbox_001",
            seat_pool_id="seatpool_sandbox_standard",
            user_id="usr_invited_001",
            status="active",
            assigned_at=datetime.now(timezone.utc),
            assigned_by_user_id="usr_admin_001",
        )
    )
    await db_session.commit()

    response = await client.get(SEATS_URL, headers=admin_headers)
    assert response.status_code == 200
    seat_summary = response.json()["seats"]
    assert seat_summary["active_assignments"] == 3
    assert "usr_invited_001" not in seat_summary["seated_user_ids"]

    users_response = await client.get(USERS_URL, headers=admin_headers)
    organization_member_by_user_id = {
        organization_member["user_id"]: organization_member
        for organization_member in users_response.json()["members"]
    }
    assert (
        organization_member_by_user_id["usr_invited_001"]["has_active_seat"]
        is False
    )


async def test_members_can_exceed_seated_users(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    organization_members = (
        await client.get(USERS_URL, headers=admin_headers)
    ).json()["members"]
    seat_summary = (
        await client.get(SEATS_URL, headers=admin_headers)
    ).json()["seats"]

    assert len(organization_members) > seat_summary["active_assignments"]
    assert any(
        not organization_member["has_active_seat"]
        for organization_member in organization_members
    )
