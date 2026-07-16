"""Workplace report-listing and report-access tool tests.

Report access belongs to the organization; the check is decided by backend
data, never by any caller input.
"""

from __future__ import annotations

from httpx import AsyncClient

REPORTS_URL = "/workplace/organizations/org_sandbox_001/reports"


def _access_url(report_id: str) -> str:
    return f"/workplace/organizations/org_sandbox_001/reports/{report_id}/access"


async def test_list_reports_annotates_access(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    resp = await client.get(REPORTS_URL, headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["access"]["permission"] == "organization.reports.read"

    reports = body["reports"]
    assert len(reports) == 5  # full catalog
    accessible = {r["report"]["id"] for r in reports if r["has_access"]}
    assert accessible == {"rpt_market_001", "rpt_market_002", "rpt_market_003"}


async def test_check_access_for_granted_report(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    resp = await client.get(_access_url("rpt_market_001"), headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["report_id"] == "rpt_market_001"
    assert body["has_access"] is True
    assert body["access_level"] == "chat"
    assert body["access_status"] == "active"


async def test_check_access_for_ungranted_report(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    resp = await client.get(_access_url("rpt_market_004"), headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["report_id"] == "rpt_market_004"
    assert body["has_access"] is False
    assert body["access_level"] is None


async def test_reader_can_list_reports(
    client: AsyncClient, reader_headers: dict[str, str]
) -> None:
    resp = await client.get(REPORTS_URL, headers=reader_headers)
    assert resp.status_code == 200
    assert len(resp.json()["reports"]) == 5


async def test_outsider_cannot_list_reports(
    client: AsyncClient, outsider_headers: dict[str, str]
) -> None:
    resp = await client.get(REPORTS_URL, headers=outsider_headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "organization_access_denied"
