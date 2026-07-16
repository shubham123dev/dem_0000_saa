"""Raw mock external API (`/mock-api/v1`) tests.

This surface simulates the future Nucleus organization API. It is read-only and
does NOT enforce Workplace-Agent permissions or require the mock auth header —
access decisions are the agent layer's responsibility, not this system of
record's.
"""

from __future__ import annotations

from httpx import AsyncClient

BASE = "/mock-api/v1/organizations/org_sandbox_001"


async def test_mock_api_needs_no_auth_header(client: AsyncClient) -> None:
    """The raw API is unauthenticated: no X-Mock-User-Id required."""

    resp = await client.get(BASE)
    assert resp.status_code == 200
    assert resp.json()["id"] == "org_sandbox_001"


async def test_mock_api_lists_users(client: AsyncClient) -> None:
    resp = await client.get(f"{BASE}/users")
    assert resp.status_code == 200
    body = resp.json()
    assert body["organization_id"] == "org_sandbox_001"
    assert len(body["users"]) == 5


async def test_mock_api_reports_seat_usage(client: AsyncClient) -> None:
    resp = await client.get(f"{BASE}/seats")
    assert resp.status_code == 200
    seats = resp.json()["seats"]
    assert seats["total_seats"] == 5
    assert seats["active_assignments"] == 3
    assert seats["available_seats"] == 2


async def test_mock_api_report_access_lists_only_granted(client: AsyncClient) -> None:
    resp = await client.get(f"{BASE}/report-access")
    assert resp.status_code == 200
    reports = resp.json()["reports"]
    assert len(reports) == 3
    assert all(r["has_access"] for r in reports)


async def test_mock_api_unknown_org_returns_404(client: AsyncClient) -> None:
    resp = await client.get("/mock-api/v1/organizations/org_missing")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "organization_not_found"
