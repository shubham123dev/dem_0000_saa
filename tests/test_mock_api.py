"""Raw mock external API (``/mock-api/v1``) tests."""

from __future__ import annotations

from httpx import AsyncClient

BASE = "/mock-api/v1/organizations/org_sandbox_001"


async def test_mock_api_needs_no_auth_header(client: AsyncClient) -> None:
    response = await client.get(BASE)
    assert response.status_code == 200
    assert response.json()["id"] == "org_sandbox_001"


async def test_mock_api_returns_complete_overview_without_workplace_context(
    client: AsyncClient,
) -> None:
    response = await client.get(f"{BASE}/overview")
    assert response.status_code == 200
    body = response.json()
    assert body["organization"]["id"] == "org_sandbox_001"
    assert body["organization"]["renewal_date"] == "2026-11-26"
    assert body["organization"]["workspace_status"] == "healthy"
    assert body["metrics"] == {
        "licensed_modules": 2,
        "available_areas": 9,
        "organization_logins": 1,
        "workspace_health_percent": 98,
    }
    assert "access" not in body
    assert "generated_at" not in body


async def test_mock_api_lists_all_seeded_memberships(client: AsyncClient) -> None:
    response = await client.get(f"{BASE}/users")
    assert response.status_code == 200
    body = response.json()
    assert body["organization_id"] == "org_sandbox_001"
    assert len(body["users"]) == 7


async def test_mock_api_reports_seat_usage(client: AsyncClient) -> None:
    response = await client.get(f"{BASE}/seats")
    assert response.status_code == 200
    seats = response.json()["seats"]
    assert seats["total_seats"] == 5
    assert seats["active_assignments"] == 3
    assert seats["available_seats"] == 2


async def test_mock_api_report_access_lists_only_granted(
    client: AsyncClient,
) -> None:
    response = await client.get(f"{BASE}/report-access")
    assert response.status_code == 200
    reports = response.json()["reports"]
    assert len(reports) == 3
    assert all(report["has_access"] for report in reports)


async def test_mock_api_unknown_org_returns_404(client: AsyncClient) -> None:
    response = await client.get("/mock-api/v1/organizations/org_missing")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "organization_not_found"

    overview_response = await client.get(
        "/mock-api/v1/organizations/org_missing/overview"
    )
    assert overview_response.status_code == 404
    assert overview_response.json()["error"]["code"] == "organization_not_found"
