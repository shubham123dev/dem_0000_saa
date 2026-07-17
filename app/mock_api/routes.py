"""Raw mock external organization API routes (``/mock-api/v1``).

These routes simulate the future Nucleus system of record. They intentionally
omit Workplace identity, permission and approval enforcement; those controls
belong to the Workplace Agent layer.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.dependencies import MockOrganizationApiDep
from app.mock_api.schemas import (
    MockAuditLogResponse,
    MockReportsResponse,
    MockSeatsResponse,
    MockUsersResponse,
)
from app.schemas.audit import AuditEventOut
from app.schemas.organization import OrganizationOut, OrganizationOverviewOut
from app.schemas.report import ReportWithAccessOut
from app.schemas.seat import SeatSummaryOut
from app.schemas.user import OrganizationMemberOut

router = APIRouter(prefix="/mock-api/v1/organizations", tags=["mock-api"])


@router.get("/{organization_id}", response_model=OrganizationOut)
async def get_organization(
    organization_id: str,
    api: MockOrganizationApiDep,
) -> OrganizationOut:
    profile = await api.get_organization(organization_id)
    return OrganizationOut.from_profile(profile)


@router.get("/{organization_id}/overview", response_model=OrganizationOverviewOut)
async def get_organization_overview(
    organization_id: str,
    api: MockOrganizationApiDep,
) -> OrganizationOverviewOut:
    overview = await api.get_overview(organization_id)
    return OrganizationOverviewOut.from_domain(overview)


@router.get("/{organization_id}/users", response_model=MockUsersResponse)
async def list_users(
    organization_id: str,
    api: MockOrganizationApiDep,
) -> MockUsersResponse:
    members = await api.list_users(organization_id)
    return MockUsersResponse(
        organization_id=organization_id,
        users=[OrganizationMemberOut.from_domain(m) for m in members],
    )


@router.get("/{organization_id}/seats", response_model=MockSeatsResponse)
async def get_seats(
    organization_id: str,
    api: MockOrganizationApiDep,
) -> MockSeatsResponse:
    summary = await api.get_seat_summary(organization_id)
    return MockSeatsResponse(
        organization_id=organization_id,
        seats=SeatSummaryOut.from_domain(summary),
    )


@router.get("/{organization_id}/reports", response_model=MockReportsResponse)
async def list_reports(
    organization_id: str,
    api: MockOrganizationApiDep,
) -> MockReportsResponse:
    reports = await api.list_reports(organization_id)
    return MockReportsResponse(
        organization_id=organization_id,
        reports=[ReportWithAccessOut.from_domain(r) for r in reports],
    )


@router.get("/{organization_id}/report-access", response_model=MockReportsResponse)
async def list_report_access(
    organization_id: str,
    api: MockOrganizationApiDep,
) -> MockReportsResponse:
    reports = await api.list_reports(organization_id)
    granted = [report for report in reports if report.has_access]
    return MockReportsResponse(
        organization_id=organization_id,
        reports=[ReportWithAccessOut.from_domain(r) for r in granted],
    )


@router.get("/{organization_id}/audit-log", response_model=MockAuditLogResponse)
async def get_audit_log(
    organization_id: str,
    api: MockOrganizationApiDep,
) -> MockAuditLogResponse:
    events = await api.get_audit_log(organization_id)
    return MockAuditLogResponse(
        organization_id=organization_id,
        events=[AuditEventOut.from_domain(event) for event in events],
    )
