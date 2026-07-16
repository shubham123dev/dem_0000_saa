"""Health, readiness, and capability endpoint tests."""

from __future__ import annotations

from httpx import AsyncClient


async def test_health_returns_200(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy"}


async def test_ready_confirms_database_connectivity(client: AsyncClient) -> None:
    resp = await client.get("/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["database"] == "connected"
    assert body["environment"] == "sandbox"


async def test_capabilities_five_read_tools_zero_write_tools(
    client: AsyncClient,
) -> None:
    resp = await client.get("/workplace/capabilities")
    assert resp.status_code == 200
    body = resp.json()
    assert body["environment"] == "sandbox"
    assert body["read_tools"] == [
        "get_organization_profile",
        "list_organization_users",
        "get_organization_seat_summary",
        "list_organization_reports",
        "check_organization_report_access",
    ]
    assert body["write_tools"] == []
    assert body["production_access"] is False
