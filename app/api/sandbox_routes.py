"""Sandbox organization routes (read-only).

Step 0 exposes only GET endpoints. No POST/PATCH/PUT/DELETE organization routes
exist here or anywhere else in the application.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.dependencies import EmployeeDep, OrganizationServiceDep
from app.domain.enums import Permission
from app.schemas.audit import AuditEventOut, AuditLogResponse
from app.schemas.organization import (
    OrganizationAccessOut,
    OrganizationOut,
    OrganizationProfileResponse,
)

router = APIRouter(prefix="/sandbox/organizations", tags=["sandbox-organizations"])


@router.get(
    "/{organization_id}/profile",
    response_model=OrganizationProfileResponse,
)
async def get_organization_profile(
    organization_id: str,
    employee: EmployeeDep,
    service: OrganizationServiceDep,
) -> OrganizationProfileResponse:
    """Read a sandbox organization profile and record a read audit event."""

    profile, access = await service.read_profile(
        employee=employee, organization_id=organization_id
    )
    return OrganizationProfileResponse(
        organization=OrganizationOut.from_profile(profile),
        access=OrganizationAccessOut(
            employee_id=access.employee_id,
            permission=Permission.ORGANIZATION_PROFILE_READ.value,
        ),
    )


@router.get(
    "/{organization_id}/audit-log",
    response_model=AuditLogResponse,
)
async def get_organization_audit_log(
    organization_id: str,
    employee: EmployeeDep,
    service: OrganizationServiceDep,
) -> AuditLogResponse:
    """Return append-only audit events scoped to the organization."""

    events = await service.list_audit_events(
        employee=employee, organization_id=organization_id
    )
    return AuditLogResponse(
        organization_id=organization_id,
        events=[AuditEventOut.from_domain(event) for event in events],
    )
