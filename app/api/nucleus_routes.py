"""Workplace routes backed by the exact-schema Nucleus SQLite mock."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from app.api.dependencies import NucleusOrganizationServiceDep, UserDep
from app.domain.enums import Permission
from app.schemas.nucleus_organization import (
    NucleusAccountResponse,
    NucleusApprovalStatusResponse,
    NucleusEntitlementsResponse,
    NucleusOrganizationApprovalStatusOut,
    NucleusOrganizationEntitlementsOut,
    NucleusOrganizationLicenseOut,
    NucleusLicenseResponse,
)
from app.schemas.organization import OrganizationAccessOut

router = APIRouter(
    prefix="/workplace/organizations/{organization_id}/nucleus",
    tags=["nucleus-organization"],
)


@router.get("/account", response_model=NucleusAccountResponse)
async def get_nucleus_organization_account(
    organization_id: str,
    user: UserDep,
    service: NucleusOrganizationServiceDep,
) -> NucleusAccountResponse:
    account, access = await service.read_account(
        user=user,
        organization_id=organization_id,
    )
    return NucleusAccountResponse.build(
        organization_id=organization_id,
        account=account,
        access=OrganizationAccessOut(
            user_id=access.user_id,
            permission=Permission.ORGANIZATION_ACCOUNT_READ.value,
        ),
    )


@router.get("/license", response_model=NucleusLicenseResponse)
async def get_nucleus_organization_license(
    organization_id: str,
    user: UserDep,
    service: NucleusOrganizationServiceDep,
) -> NucleusLicenseResponse:
    license_info, access = await service.read_license(
        user=user,
        organization_id=organization_id,
    )
    return NucleusLicenseResponse(
        organization_id=organization_id,
        license=NucleusOrganizationLicenseOut.from_domain(license_info),
        access=OrganizationAccessOut(
            user_id=access.user_id,
            permission=Permission.ORGANIZATION_ACCOUNT_READ.value,
        ),
        generated_at=datetime.now(timezone.utc),
    )


@router.get("/approval-status", response_model=NucleusApprovalStatusResponse)
async def get_nucleus_organization_approval_status(
    organization_id: str,
    user: UserDep,
    service: NucleusOrganizationServiceDep,
) -> NucleusApprovalStatusResponse:
    approval, access = await service.read_approval_status(
        user=user,
        organization_id=organization_id,
    )
    return NucleusApprovalStatusResponse(
        organization_id=organization_id,
        approval=NucleusOrganizationApprovalStatusOut.from_domain(approval),
        access=OrganizationAccessOut(
            user_id=access.user_id,
            permission=Permission.ORGANIZATION_ACCOUNT_READ.value,
        ),
        generated_at=datetime.now(timezone.utc),
    )


@router.get("/entitlements", response_model=NucleusEntitlementsResponse)
async def get_nucleus_organization_entitlements(
    organization_id: str,
    user: UserDep,
    service: NucleusOrganizationServiceDep,
) -> NucleusEntitlementsResponse:
    entitlements, access = await service.read_entitlements(
        user=user,
        organization_id=organization_id,
    )
    return NucleusEntitlementsResponse(
        organization_id=organization_id,
        entitlements=NucleusOrganizationEntitlementsOut.from_domain(entitlements),
        access=OrganizationAccessOut(
            user_id=access.user_id,
            permission=Permission.ORGANIZATION_ENTITLEMENTS_READ.value,
        ),
        generated_at=datetime.now(timezone.utc),
    )
