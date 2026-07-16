"""Idempotent seed for deterministic synthetic sandbox data.

Run as a module::

    python -m app.db.seed

Seeding is idempotent: running it twice never produces duplicate data. The
seed function accepts an existing ``AsyncSession`` so tests can reuse it against
isolated temporary databases.

Seed shape (proves users != seats):
    - 1 organization (org_sandbox_001)
    - 1 standard seat pool with 5 total seats
    - 6 users, 5 memberships (1 invited), 1 outsider with no membership
    - 3 active seat assignments (usage 3 < capacity 5, users 6 > seats 5)
    - 5 catalog reports; organization has access to 3 (2 inaccessible)
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base
from app.db.orm_models import (
    AuditEventORM,  # noqa: F401  (ensures table is registered on metadata)
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

# --- Deterministic synthetic seed data -------------------------------------

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
    "organization_id": "org_sandbox_001",
    "seat_type": SeatType.STANDARD.value,
    "total_seats": 5,
    "status": SeatPoolStatus.ACTIVE.value,
    "starts_at": _EPOCH,
    "expires_at": None,
}

USERS = [
    {
        "id": "usr_admin_001",
        "display_name": "Sandbox Admin",
        "email": "admin@example.test",
        "status": UserStatus.ACTIVE.value,
    },
    {
        "id": "usr_member_001",
        "display_name": "Seated Member One",
        "email": "member1@example.test",
        "status": UserStatus.ACTIVE.value,
    },
    {
        "id": "usr_member_002",
        "display_name": "Seated Member Two",
        "email": "member2@example.test",
        "status": UserStatus.ACTIVE.value,
    },
    {
        "id": "usr_member_003",
        "display_name": "Unseated Member",
        "email": "member3@example.test",
        "status": UserStatus.ACTIVE.value,
    },
    {
        "id": "usr_invited_001",
        "display_name": "Invited Member",
        "email": "invited@example.test",
        "status": UserStatus.ACTIVE.value,
    },
    {
        "id": "usr_outsider_001",
        "display_name": "Outsider User",
        "email": "outsider@example.test",
        "status": UserStatus.ACTIVE.value,
    },
]

# (user_id, role, membership_status) — the outsider intentionally has none.
MEMBERSHIPS = [
    ("usr_admin_001", Role.SANDBOX_ADMIN.value, MembershipStatus.ACTIVE.value),
    ("usr_member_001", Role.SANDBOX_READER.value, MembershipStatus.ACTIVE.value),
    ("usr_member_002", Role.SANDBOX_READER.value, MembershipStatus.ACTIVE.value),
    ("usr_member_003", Role.SANDBOX_READER.value, MembershipStatus.ACTIVE.value),
    ("usr_invited_001", Role.SANDBOX_READER.value, MembershipStatus.INVITED.value),
]

# Only these users consume seats (usr_member_003 is an active member WITHOUT a
# seat; the invited user and outsider hold none).
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

# The organization can access 3 of the 5 reports (rpt_market_004/005 excluded).
REPORT_ACCESS = [
    ("orgacc_001", "rpt_market_001", ReportAccessLevel.CHAT.value),
    ("orgacc_002", "rpt_market_002", ReportAccessLevel.VIEW.value),
    ("orgacc_003", "rpt_market_003", ReportAccessLevel.FULL.value),
]


async def _upsert_organization(session: AsyncSession) -> None:
    if await session.get(OrganizationORM, ORGANIZATION["id"]) is None:
        session.add(OrganizationORM(**ORGANIZATION))


async def _upsert_seat_pool(session: AsyncSession) -> None:
    if await session.get(OrganizationSeatPoolORM, SEAT_POOL["id"]) is None:
        session.add(OrganizationSeatPoolORM(**SEAT_POOL))


async def _upsert_users(session: AsyncSession) -> None:
    for data in USERS:
        if await session.get(UserORM, data["id"]) is None:
            session.add(UserORM(**data))


async def _upsert_memberships(session: AsyncSession) -> None:
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


async def _upsert_seat_assignments(session: AsyncSession) -> None:
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


async def _upsert_reports(session: AsyncSession) -> None:
    for report_id, external_id, title, market in REPORTS:
        if await session.get(ReportORM, report_id) is None:
            session.add(
                ReportORM(
                    id=report_id,
                    external_report_id=external_id,
                    title=title,
                    market_name=market,
                    status=ReportStatus.ACTIVE.value,
                )
            )


async def _upsert_report_access(session: AsyncSession) -> None:
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


async def _upsert_role_permissions(session: AsyncSession) -> None:
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


async def seed(session: AsyncSession) -> None:
    """Idempotently seed all synthetic data into the provided session."""

    await _upsert_organization(session)
    await _upsert_seat_pool(session)
    await _upsert_users(session)
    await _upsert_memberships(session)
    await _upsert_seat_assignments(session)
    await _upsert_reports(session)
    await _upsert_report_access(session)
    await _upsert_role_permissions(session)
    await session.commit()


async def _run() -> None:
    engine = get_engine()
    # Ensure tables exist even if the seed is run before/without Alembic.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        await seed(session)
    await engine.dispose()
    print("Seed complete (idempotent). Organization: org_sandbox_001")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
