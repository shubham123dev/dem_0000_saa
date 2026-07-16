"""Workplace users and seat-summary tool tests.

Proves the core business rule: users and seats are distinct. The org has more
users than seats, and seat usage is computed from active assignments.
"""

from __future__ import annotations

from httpx import AsyncClient

USERS_URL = "/workplace/organizations/org_sandbox_001/users"
SEATS_URL = "/workplace/organizations/org_sandbox_001/seats"


async def test_list_users_returns_all_memberships(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    resp = await client.get(USERS_URL, headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["access"]["permission"] == "organization.users.read"

    members = body["members"]
    # 5 memberships (the outsider has none).
    assert len(members) == 5
    by_id = {m["user_id"]: m for m in members}
    assert set(by_id) == {
        "usr_admin_001",
        "usr_member_001",
        "usr_member_002",
        "usr_member_003",
        "usr_invited_001",
    }


async def test_users_and_seats_are_distinct(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    body = (await client.get(USERS_URL, headers=admin_headers)).json()
    by_id = {m["user_id"]: m for m in body["members"]}

    # Seated members.
    assert by_id["usr_admin_001"]["has_active_seat"] is True
    assert by_id["usr_member_001"]["has_active_seat"] is True
    assert by_id["usr_member_002"]["has_active_seat"] is True
    # Active member WITHOUT a seat.
    assert by_id["usr_member_003"]["has_active_seat"] is False
    # Invited member: not active, no seat.
    assert by_id["usr_invited_001"]["membership_status"] == "invited"
    assert by_id["usr_invited_001"]["has_active_seat"] is False


async def test_seat_summary_is_computed(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    resp = await client.get(SEATS_URL, headers=admin_headers)
    assert resp.status_code == 200
    seats = resp.json()["seats"]

    assert seats["seat_type"] == "standard"
    assert seats["total_seats"] == 5
    assert seats["active_assignments"] == 3
    # available = total - active, never stored.
    assert seats["available_seats"] == 2
    assert sorted(seats["seated_user_ids"]) == [
        "usr_admin_001",
        "usr_member_001",
        "usr_member_002",
    ]


async def test_members_can_exceed_seated_users(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    """More members exist than occupy seats: membership != seat entitlement."""

    users = (await client.get(USERS_URL, headers=admin_headers)).json()["members"]
    seats = (await client.get(SEATS_URL, headers=admin_headers)).json()["seats"]
    # 5 members, only 3 hold active seats -> unseated members exist.
    assert len(users) > seats["active_assignments"]
    assert any(not m["has_active_seat"] for m in users)
