"""Idempotent deterministic seed for the migrated sandbox database.

Run only after ``alembic upgrade head``::

    alembic upgrade head
    python -m app.db.seed

The seed intentionally does not call ``Base.metadata.create_all``. Alembic is
the only application schema authority; tests may create isolated schemas from
metadata in their own fixtures.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.nucleus_admin_models import NucleusActorMappingORM
from app.db.nucleus_models import (
    NucleusOrganizationAccountORM,
    NucleusOrganizationCategoryAccessORM,
    NucleusOrganizationCompanyProfileAccessORM,
    NucleusOrganizationDrugAccessORM,
    NucleusOrganizationIndicationAccessORM,
    NucleusOrganizationMarketAccessORM,
    NucleusOrganizationPermissionORM,
    NucleusOrganizationReportAccessORM,
    NucleusResourceVersionORM,
)
from app.db.orm_models import (
    OrganizationMembershipORM,
    OrganizationORM,
    OrganizationOverviewORM,
    OrganizationReportAccessORM,
    OrganizationSeatPoolORM,
    ReportORM,
    RolePermissionORM,
    SeatAssignmentORM,
    UserORM,
)
from app.db.session import get_engine, get_sessionmaker
from app.domain.enums import (
    ROLE_PERMISSIONS,
    Environment,
    MembershipStatus,
    OrganizationStatus,
    ReportAccessLevel,
    ReportAccessStatus,
    ReportStatus,
    Role,
    SeatAssignmentStatus,
    SeatPoolStatus,
    SeatType,
    UserStatus,
    WorkspaceHealthStatus,
)

_EPOCH = datetime(2026, 1, 1, tzinfo=timezone.utc)

ORGANIZATION = {
    "id": "org_sandbox_001",
    "display_name": "Demo Enterprise Sandbox",
    "legal_name": "Demo Enterprise Private Limited",
    "contact_email": "operations@example.test",
    "environment": Environment.SANDBOX.value,
    "status": OrganizationStatus.ACTIVE.value,
    "version": 1,
}

ORGANIZATION_OVERVIEW = {
    "organization_id": ORGANIZATION["id"],
    "organization_type": "organization",
    "renewal_date": date(2026, 11, 26),
    "workspace_status": WorkspaceHealthStatus.HEALTHY.value,
    "workspace_health_percent": 98,
    "licensed_modules": 2,
    "available_areas": 9,
    "organization_logins": 1,
    "version": 1,
}

SEAT_POOL = {
    "id": "seatpool_sandbox_standard",
    "organization_id": ORGANIZATION["id"],
    "seat_type": SeatType.STANDARD.value,
    "total_seats": 5,
    "status": SeatPoolStatus.ACTIVE.value,
    "starts_at": _EPOCH,
    "expires_at": None,
}

USERS = [
    ("usr_admin_001", "Sandbox Admin", "admin@example.test"),
    (
        "usr_approval_admin_001",
        "Approval Admin One",
        "approval.admin1@example.test",
    ),
    (
        "usr_approval_admin_002",
        "Approval Admin Two",
        "approval.admin2@example.test",
    ),
    ("usr_member_001", "Seated Member One", "member1@example.test"),
    ("usr_member_002", "Seated Member Two", "member2@example.test"),
    ("usr_member_003", "Unseated Member", "member3@example.test"),
    ("usr_invited_001", "Invited Member", "invited@example.test"),
    ("usr_outsider_001", "Outsider User", "outsider@example.test"),
]

NUCLEUS_ACTOR_MAPPINGS = (
    ("usr_admin_001", 1001),
    ("usr_approval_admin_001", 1002),
    ("usr_approval_admin_002", 1003),
)
MEMBERSHIPS = [
    ("usr_admin_001", Role.SANDBOX_ADMIN.value, MembershipStatus.ACTIVE.value),
    (
        "usr_approval_admin_001",
        Role.SANDBOX_ADMIN.value,
        MembershipStatus.ACTIVE.value,
    ),
    (
        "usr_approval_admin_002",
        Role.SANDBOX_ADMIN.value,
        MembershipStatus.ACTIVE.value,
    ),
    ("usr_member_001", Role.SANDBOX_READER.value, MembershipStatus.ACTIVE.value),
    ("usr_member_002", Role.SANDBOX_READER.value, MembershipStatus.ACTIVE.value),
    ("usr_member_003", Role.SANDBOX_READER.value, MembershipStatus.ACTIVE.value),
    ("usr_invited_001", Role.SANDBOX_READER.value, MembershipStatus.INVITED.value),
]

SEAT_ASSIGNMENTS = [
    ("seat_admin_001", "usr_admin_001"),
    ("seat_member_001", "usr_member_001"),
    ("seat_member_002", "usr_member_002"),
]

REPORTS = [
    ("rpt_market_001", "RPT-1001", "Global EV Battery Market", "EV Batteries"),
    (
        "rpt_market_002",
        "RPT-1002",
        "Industrial Automation Outlook",
        "Automation",
    ),
    (
        "rpt_market_003",
        "RPT-1003",
        "Biopharma Pipeline Analysis",
        "Biopharma",
    ),
    (
        "rpt_market_004",
        "RPT-1004",
        "Renewable Hydrogen Forecast",
        "Hydrogen",
    ),
    (
        "rpt_market_005",
        "RPT-1005",
        "Semiconductor Supply Chain",
        "Semiconductors",
    ),
]

REPORT_ACCESS = [
    ("orgacc_001", "rpt_market_001", ReportAccessLevel.CHAT.value),
    ("orgacc_002", "rpt_market_002", ReportAccessLevel.VIEW.value),
    ("orgacc_003", "rpt_market_003", ReportAccessLevel.FULL.value),
]


NUCLEUS_ORGANIZATION_ACCOUNT = {
    "organization_account_id": 1,
    "organization_name": "Demo Enterprise Sandbox",
    "organization_code": ORGANIZATION["id"],
    "organization_type": "Enterprise",
    "industry": "Market Research",
    "website": "https://example.test",
    "user_name": "sandbox.organization",
    "password": "$mock$not-a-real-password",
    "email": "operations@example.test",
    "contact_person_name": "Sandbox Operations",
    "contact_person_designation": "Operations Administrator",
    "contact_phone": "+91-00000-00000",
    "address_line1": "Synthetic Address Line 1",
    "address_line2": None,
    "city": "Jaipur",
    "state": "Rajasthan",
    "country": "India",
    "postal_code": "000000",
    "max_user_limit": 5,
    "license_start_date": _EPOCH,
    "license_end_date": datetime(2026, 11, 26, tzinfo=timezone.utc),
    "status": "approved",
    "approved_by": 1001,
    "approved_date": _EPOCH,
    "rejected_by": None,
    "rejected_date": None,
    "rejection_reason": None,
    "is_active": True,
    "created_by": 1001,
    "created_date": _EPOCH,
    "updated_by": None,
    "updated_date": None,
}

NUCLEUS_CATEGORY_ACCESS = [
    {
        "organization_category_access_id": 1,
        "organization_account_id": 1,
        "category_id": 101,
        "category_sample_id": 1001,
        "created_date": _EPOCH,
        "is_active": True,
    }
]

NUCLEUS_COMPANY_PROFILE_ACCESS = [
    {
        "organization_company_profile_access_id": 1,
        "organization_account_id": 1,
        "company_id": 201,
    }
]

NUCLEUS_DRUG_ACCESS = [
    {
        "organization_drug_access_id": 1,
        "organization_account_id": 1,
        "drug_id": 301,
    }
]

NUCLEUS_INDICATION_ACCESS = [
    {
        "organization_indication_access_id": 1,
        "organization_account_id": 1,
        "indication_id": 401,
    }
]

NUCLEUS_MARKET_ACCESS = [
    {
        "organization_market_access_id": 1,
        "organization_account_id": 1,
        "market_id": 501,
        "market_sample_id": 5001,
    }
]

NUCLEUS_PERMISSIONS = [
    {
        "organization_permission_id": 1,
        "organization_account_id": 1,
        "cp_company_master_pharma_id": 601,
        "hc_theropetic_category_pharma_id": 602,
        "hc_theropetic_category_epidem_id": 603,
        "hc_disease_code_epidem_id": 604,
        "reports_custom_id": 605,
        "importexport_report_id": 606,
        "created_date": _EPOCH,
        "is_active": True,
    }
]

NUCLEUS_REPORT_ACCESS = [
    {
        "organization_report_access_id": 1,
        "organization_account_id": 1,
        "reports_id": 1001,
        "sample_id": 1101,
        "sample_toc_id": 1201,
        "speciality_id": 1301,
        "is_executive_access": True,
        "created_date": _EPOCH,
        "is_active": True,
    }
]


async def seed(session: AsyncSession) -> None:
    """Idempotently seed all synthetic sandbox rows."""

    if await session.get(OrganizationORM, ORGANIZATION["id"]) is None:
        session.add(OrganizationORM(**ORGANIZATION))

    await session.flush()

    if (
        await session.get(
            OrganizationOverviewORM,
            ORGANIZATION_OVERVIEW["organization_id"],
        )
        is None
    ):
        session.add(OrganizationOverviewORM(**ORGANIZATION_OVERVIEW))

    if await session.get(OrganizationSeatPoolORM, SEAT_POOL["id"]) is None:
        session.add(OrganizationSeatPoolORM(**SEAT_POOL))

    for user_id, display_name, email in USERS:
        if await session.get(UserORM, user_id) is None:
            session.add(
                UserORM(
                    id=user_id,
                    display_name=display_name,
                    email=email,
                    status=UserStatus.ACTIVE.value,
                )
            )

    await session.flush()

    for workplace_user_id, nucleus_actor_id in NUCLEUS_ACTOR_MAPPINGS:
        if (
            await session.get(NucleusActorMappingORM, workplace_user_id)
            is None
        ):
            session.add(
                NucleusActorMappingORM(
                    workplace_user_id=workplace_user_id,
                    nucleus_actor_id=nucleus_actor_id,
                    created_at=_EPOCH,
                    updated_at=_EPOCH,
                )
            )

    for user_id, role, membership_status in MEMBERSHIPS:
        statement = select(OrganizationMembershipORM).where(
            OrganizationMembershipORM.organization_id == ORGANIZATION["id"],
            OrganizationMembershipORM.user_id == user_id,
        )
        if (await session.execute(statement)).scalar_one_or_none() is None:
            session.add(
                OrganizationMembershipORM(
                    organization_id=ORGANIZATION["id"],
                    user_id=user_id,
                    role=role,
                    membership_status=membership_status,
                    joined_at=_EPOCH,
                )
            )

    for assignment_id, user_id in SEAT_ASSIGNMENTS:
        if await session.get(SeatAssignmentORM, assignment_id) is None:
            session.add(
                SeatAssignmentORM(
                    id=assignment_id,
                    organization_id=ORGANIZATION["id"],
                    seat_pool_id=SEAT_POOL["id"],
                    user_id=user_id,
                    status=SeatAssignmentStatus.ACTIVE.value,
                    assigned_at=_EPOCH,
                    assigned_by_user_id="usr_admin_001",
                )
            )

    for report_id, external_id, title, market_name in REPORTS:
        if await session.get(ReportORM, report_id) is None:
            session.add(
                ReportORM(
                    id=report_id,
                    external_report_id=external_id,
                    title=title,
                    market_name=market_name,
                    status=ReportStatus.ACTIVE.value,
                )
            )

    await session.flush()

    for access_id, report_id, access_level in REPORT_ACCESS:
        if await session.get(OrganizationReportAccessORM, access_id) is None:
            session.add(
                OrganizationReportAccessORM(
                    id=access_id,
                    organization_id=ORGANIZATION["id"],
                    report_id=report_id,
                    access_level=access_level,
                    status=ReportAccessStatus.ACTIVE.value,
                    granted_at=_EPOCH,
                    granted_by_user_id="usr_admin_001",
                )
            )

    if await session.get(
        NucleusOrganizationAccountORM,
        NUCLEUS_ORGANIZATION_ACCOUNT["organization_account_id"],
    ) is None:
        session.add(NucleusOrganizationAccountORM(**NUCLEUS_ORGANIZATION_ACCOUNT))

    await session.flush()

    for values in NUCLEUS_CATEGORY_ACCESS:
        if await session.get(
            NucleusOrganizationCategoryAccessORM,
            values["organization_category_access_id"],
        ) is None:
            session.add(NucleusOrganizationCategoryAccessORM(**values))

    for values in NUCLEUS_COMPANY_PROFILE_ACCESS:
        if await session.get(
            NucleusOrganizationCompanyProfileAccessORM,
            values["organization_company_profile_access_id"],
        ) is None:
            session.add(NucleusOrganizationCompanyProfileAccessORM(**values))

    for values in NUCLEUS_DRUG_ACCESS:
        if await session.get(
            NucleusOrganizationDrugAccessORM,
            values["organization_drug_access_id"],
        ) is None:
            session.add(NucleusOrganizationDrugAccessORM(**values))

    for values in NUCLEUS_INDICATION_ACCESS:
        if await session.get(
            NucleusOrganizationIndicationAccessORM,
            values["organization_indication_access_id"],
        ) is None:
            session.add(NucleusOrganizationIndicationAccessORM(**values))

    for values in NUCLEUS_MARKET_ACCESS:
        if await session.get(
            NucleusOrganizationMarketAccessORM,
            values["organization_market_access_id"],
        ) is None:
            session.add(NucleusOrganizationMarketAccessORM(**values))

    for values in NUCLEUS_PERMISSIONS:
        if await session.get(
            NucleusOrganizationPermissionORM,
            values["organization_permission_id"],
        ) is None:
            session.add(NucleusOrganizationPermissionORM(**values))

    for values in NUCLEUS_REPORT_ACCESS:
        if await session.get(
            NucleusOrganizationReportAccessORM,
            values["organization_report_access_id"],
        ) is None:
            session.add(NucleusOrganizationReportAccessORM(**values))

    await session.flush()

    nucleus_versions = [
        ("nucleus_account", "1"),
        ("nucleus_category_access", "1"),
        ("nucleus_company_profile_access", "1"),
        ("nucleus_drug_access", "1"),
        ("nucleus_indication_access", "1"),
        ("nucleus_market_access", "1"),
        ("nucleus_special_permissions", "1"),
        ("nucleus_report_access", "1"),
    ]
    for resource_type, resource_key in nucleus_versions:
        version_row = await session.get(
            NucleusResourceVersionORM,
            {"resource_type": resource_type, "resource_key": resource_key},
        )
        if version_row is None:
            session.add(
                NucleusResourceVersionORM(
                    resource_type=resource_type,
                    resource_key=resource_key,
                    version=1,
                    updated_at=_EPOCH,
                )
            )

    for role, permissions in ROLE_PERMISSIONS.items():
        for permission in permissions:
            statement = select(RolePermissionORM).where(
                RolePermissionORM.role == role.value,
                RolePermissionORM.permission == permission.value,
            )
            if (await session.execute(statement)).scalar_one_or_none() is None:
                session.add(
                    RolePermissionORM(role=role.value, permission=permission.value)
                )

    await session.commit()


async def _run() -> None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        await seed(session)
    await get_engine().dispose()
    print("Seed complete (idempotent). Organization: org_sandbox_001")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
