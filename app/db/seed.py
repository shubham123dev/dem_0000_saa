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
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.orm_models import (
    OrganizationMembershipORM,
    OrganizationORM,
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
    ("usr_approval_admin_001", "Approval Admin One", "approval.admin1@example.test"),
    ("usr_approval_admin_002", "Approval Admin Two", "approval.admin2@example.test"),
    ("usr_member_001", "Seated Member One", "member1@example.test"),
    ("usr_member_002", "Seated Member Two", "member2@example.test"),
    ("usr_member_003", "Unseated Member", "member3@example.test"),
    ("usr_invited_001", "Invited Member", "invited@example.test"),
    ("usr_outsider_001", "Outsider User", "outsider@example.test"),
]

MEMBERSHIPS = [
    ("usr_admin_001", Role.SANDBOX_ADMIN.value, MembershipStatus.ACTIVE.value),
    ("usr_approval_admin_001", Role.SANDBOX_ADMIN.value, MembershipStatus.ACTIVE.value),
    ("usr_approval_admin_002", Role.SANDBOX_ADMIN.value, MembershipStatus.ACTIVE.value),
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
    ("rpt_market_002", "RPT-1002", "Industrial Automation Outlook", "Automation"),
    ("rpt_market_003", "RPT-1003", "Biopharma Pipeline Analysis", "Biopharma"),
    ("rpt_market_004", "RPT-1004", "Renewable Hydrogen Forecast", "Hydrogen"),
    ("rpt_market_005", "RPT-1005", "Semiconductor Supply Chain", "Semiconductors"),
]

REPORT_ACCESS = [
    ("orgacc_001", "rpt_market_001", ReportAccessLevel.CHAT.value),
    ("orgacc_002", "rpt_market_002", ReportAccessLevel.VIEW.value),
    ("orgacc_003", "rpt_market_003", ReportAccessLevel.FULL.value),
]


async def seed(session: AsyncSession) -> None:
    """Idempotently seed all synthetic sandbox rows."""

    if await session.get(OrganizationORM, ORGANIZATION["id"]) is None:
        session.add(OrganizationORM(**ORGANIZATION))

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

    for user_id, role, membership_status in MEMBERSHIPS:
        stmt = select(OrganizationMembershipORM).where(
            OrganizationMembershipORM.organization_id == ORGANIZATION["id"],
            OrganizationMembershipORM.user_id == user_id,
        )
        if (await session.execute(stmt)).scalar_one_or_none() is None:
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

    for role, permissions in ROLE_PERMISSIONS.items():
        for permission in permissions:
            stmt = select(RolePermissionORM).where(
                RolePermissionORM.role == role.value,
                RolePermissionORM.permission == permission.value,
            )
            if (await session.execute(stmt)).scalar_one_or_none() is None:
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
