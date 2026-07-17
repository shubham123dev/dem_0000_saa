from __future__ import annotations

from datetime import datetime, timedelta, timezone

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.orm_models import OrganizationReportAccessORM, ReportORM

REPORTS_URL = "/workplace/organizations/org_sandbox_001/reports"


def build_report_access_url(report_id: str) -> str:
    return f"/workplace/organizations/org_sandbox_001/reports/{report_id}/access"


async def test_list_reports_annotates_current_access(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    response = await client.get(REPORTS_URL, headers=admin_headers)

    assert response.status_code == 200
    response_body = response.json()
    assert response_body["access"]["permission"] == "organization.reports.read"

    organization_reports = response_body["reports"]
    assert len(organization_reports) == 5
    accessible_report_ids = {
        organization_report["report"]["id"]
        for organization_report in organization_reports
        if organization_report["has_access"]
    }
    assert accessible_report_ids == {
        "rpt_market_001",
        "rpt_market_002",
        "rpt_market_003",
    }


async def test_retired_reports_are_not_returned(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    retired_report = await db_session.get(ReportORM, "rpt_market_005")
    assert retired_report is not None
    retired_report.status = "retired"
    await db_session.commit()

    response = await client.get(REPORTS_URL, headers=admin_headers)

    assert response.status_code == 200
    returned_report_ids = {
        organization_report["report"]["id"]
        for organization_report in response.json()["reports"]
    }
    assert "rpt_market_005" not in returned_report_ids
    assert len(returned_report_ids) == 4


async def test_check_access_for_granted_report(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    response = await client.get(
        build_report_access_url("rpt_market_001"),
        headers=admin_headers,
    )

    assert response.status_code == 200
    response_body = response.json()
    assert response_body["report_id"] == "rpt_market_001"
    assert response_body["has_access"] is True
    assert response_body["access_level"] == "chat"
    assert response_body["access_status"] == "active"


async def test_expired_report_access_is_denied(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    organization_report_access = await db_session.get(
        OrganizationReportAccessORM,
        "orgacc_001",
    )
    assert organization_report_access is not None
    organization_report_access.expires_at = datetime.now(timezone.utc) - timedelta(
        minutes=1
    )
    await db_session.commit()

    response = await client.get(
        build_report_access_url("rpt_market_001"),
        headers=admin_headers,
    )

    assert response.status_code == 200
    response_body = response.json()
    assert response_body["has_access"] is False
    assert response_body["access_level"] == "chat"
    assert response_body["access_status"] == "expired"

    report_list_response = await client.get(REPORTS_URL, headers=admin_headers)
    report_access_by_report_id = {
        organization_report["report"]["id"]: organization_report
        for organization_report in report_list_response.json()["reports"]
    }
    assert report_access_by_report_id["rpt_market_001"]["has_access"] is False
    assert report_access_by_report_id["rpt_market_001"]["access_level"] is None
    assert report_access_by_report_id["rpt_market_001"]["access_status"] is None


async def test_check_access_for_existing_ungranted_report(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    response = await client.get(
        build_report_access_url("rpt_market_004"),
        headers=admin_headers,
    )

    assert response.status_code == 200
    response_body = response.json()
    assert response_body["report_id"] == "rpt_market_004"
    assert response_body["has_access"] is False
    assert response_body["access_level"] is None
    assert response_body["access_status"] is None


async def test_unknown_report_returns_report_not_found(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    response = await client.get(
        build_report_access_url("rpt_missing_999"),
        headers=admin_headers,
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "report_not_found"


async def test_retired_report_returns_report_not_found(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    retired_report = await db_session.get(ReportORM, "rpt_market_001")
    assert retired_report is not None
    retired_report.status = "retired"
    await db_session.commit()

    response = await client.get(
        build_report_access_url("rpt_market_001"),
        headers=admin_headers,
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "report_not_found"


async def test_reader_can_list_reports(
    client: AsyncClient,
    reader_headers: dict[str, str],
) -> None:
    response = await client.get(REPORTS_URL, headers=reader_headers)

    assert response.status_code == 200
    assert len(response.json()["reports"]) == 5


async def test_outsider_cannot_list_reports(
    client: AsyncClient,
    outsider_headers: dict[str, str],
) -> None:
    response = await client.get(REPORTS_URL, headers=outsider_headers)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "organization_access_denied"
