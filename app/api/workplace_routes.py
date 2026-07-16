"""Workplace-Agent tool routes (read-only, permission-enforced).

These are the enforced Workplace-Agent tools. Unlike the raw ``/mock-api/v1``
surface, every endpoint here resolves the org, blocks production, and authorizes
the user (active membership + required permission) before returning data.

Step 0 exposes only GET endpoints. No POST/PATCH/PUT/DELETE routes exist.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.dependencies import OrganizationServiceDep, UserDep
from app.domain.enums import Permission
from app.schemas.audit import AuditEventOut, AuditLogResponse
from app.schemas.organization import (
    OrganizationAccessOut,
    OrganizationOut,
    OrganizationProfileResponse,
)
from app.schemas.report import (
    OrganizationReportsResponse,
    ReportAccessResponse,
    ReportWithAccessOut,
)
from app.schemas.seat import OrganizationSeatsResponse, SeatSummaryOut
from app.schemas.user import OrganizationMemberOut, OrganizationUsersResponse

router = APIRouter(prefix="/workplace/organizations", tags=["workplace"])


@router.get("/{organization_id}/profile", response_model=OrganizationProfileResponse)
async def get_organization_profile(
    organization_id: str,
    user: UserDep,
    service: OrganizationServiceDep,
) -> OrganizationProfileResponse:
    """Tool: ``get_organization_profile``."""

    profile, access = await service.read_profile(
        user=user, organization_id=organization_id
    )
    return OrganizationProfileResponse(
        organization=OrganizationOut.from_profile(profile),
        access=OrganizationAccessOut(
            user_id=access.user_id,
            permission=Permission.ORGANIZATION_PROFILE_READ.value,
        ),
    )


@router.get("/{organization_id}/users", response_model=OrganizationUsersResponse)
async def list_organization_users(
    organization_id: str,
    user: UserDep,
    service: OrganizationServiceDep,
) -> OrganizationUsersResponse:
    """Tool: ``list_organization_users``."""

    members, access = await service.list_users(
        user=user, organization_id=organization_id
    )
    return OrganizationUsersResponse(
        organization_id=organization_id,
        members=[OrganizationMemberOut.from_domain(m) for m in members],
        access=OrganizationAccessOut(
            user_id=access.user_id,
            permission=Permission.ORGANIZATION_USERS_READ.value,
        ),
    )


@router.get("/{organization_id}/seats", response_model=OrganizationSeatsResponse)
async def get_organization_seat_summary(
    organization_id: str,
    user: UserDep,
    service: OrganizationServiceDep,
) -> OrganizationSeatsResponse:
    """Tool: ``get_organization_seat_summary``."""

    summary, access = await service.get_seat_summary(
        user=user, organization_id=organization_id
    )
    return OrganizationSeatsResponse(
        organization_id=organization_id,
        seats=SeatSummaryOut.from_domain(summary),
        access=OrganizationAccessOut(
            user_id=access.user_id,
            permission=Permission.ORGANIZATION_SEATS_READ.value,
        ),
    )


@router.get("/{organization_id}/reports", response_model=OrganizationReportsResponse)
async def list_organization_reports(
    organization_id: str,
    user: UserDep,
    service: OrganizationServiceDep,
) -> OrganizationReportsResponse:
    """Tool: ``list_organization_reports``."""

    reports, access = await service.list_reports(
        user=user, organization_id=organization_id
    )
    return OrganizationReportsResponse(
        organization_id=organization_id,
        reports=[ReportWithAccessOut.from_domain(r) for r in reports],
        access=OrganizationAccessOut(
            user_id=access.user_id,
            permission=Permission.ORGANIZATION_REPORTS_READ.value,
        ),
    )


@router.get(
    "/{organization_id}/reports/{report_id}/access",
    response_model=ReportAccessResponse,
)
async def check_organization_report_access(
    organization_id: str,
    report_id: str,
    user: UserDep,
    service: OrganizationServiceDep,
) -> ReportAccessResponse:
    """Tool: ``check_organization_report_access``."""

    decision, access = await service.check_report_access(
        user=user, organization_id=organization_id, report_id=report_id
    )
    return ReportAccessResponse.from_decision(
        decision,
        OrganizationAccessOut(
            user_id=access.user_id,
            permission=Permission.ORGANIZATION_REPORTS_READ.value,
        ),
    )


@router.get("/{organization_id}/audit-log", response_model=AuditLogResponse)
async def get_organization_audit_log(
    organization_id: str,
    user: UserDep,
    service: OrganizationServiceDep,
) -> AuditLogResponse:
    """Return append-only audit events scoped to the organization."""

    events, _access = await service.list_audit_events(
        user=user, organization_id=organization_id
    )
    return AuditLogResponse(
        organization_id=organization_id,
        events=[AuditEventOut.from_domain(event) for event in events],
    )
