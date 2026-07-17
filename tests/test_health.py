"""Health, readiness, and capability endpoint tests."""

from __future__ import annotations

from httpx import AsyncClient

EXPECTED_READ_TOOLS = [
    "get_organization_overview",
    "get_organization_profile",
    "list_organization_users",
    "get_organization_seat_summary",
    "list_organization_reports",
    "check_organization_report_access",
    "get_organization_audit_log",
]

EXPECTED_WRITE_ACTIONS = {
    "update_organization_contact_email",
    "invite_organization_user",
    "activate_organization_membership",
    "update_organization_member_role",
    "remove_organization_user",
    "assign_organization_seat",
    "revoke_organization_seat",
    "grant_organization_report_access",
    "revoke_organization_report_access",
}


async def test_health_returns_200(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


async def test_ready_confirms_database_connectivity(client: AsyncClient) -> None:
    response = await client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["database"] == "connected"
    assert body["environment"] == "sandbox"


async def test_capabilities_advertise_complete_current_surface(
    client: AsyncClient,
) -> None:
    response = await client.get("/workplace/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert body["environment"] == "sandbox"
    assert body["read_tools"] == EXPECTED_READ_TOOLS
    assert set(body["write_tools"]) == EXPECTED_WRITE_ACTIONS
    assert {item["name"] for item in body["write_actions"]} == EXPECTED_WRITE_ACTIONS
    assert body["approval_required"] is True
    assert body["production_access"] is False
