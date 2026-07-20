from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.orm_models import (
    OrganizationMembershipORM,
    OrganizationReportAccessORM,
    SeatAssignmentORM,
)


async def test_duplicate_organization_membership_is_rejected(
    db_session: AsyncSession,
    seeded,
) -> None:
    current_timestamp = datetime.now(timezone.utc)
    db_session.add(
        OrganizationMembershipORM(
            organization_id="org_sandbox_001",
            user_id="usr_member_001",
            role="sandbox_admin",
            membership_status="active",
            joined_at=current_timestamp,
            created_at=current_timestamp,
            updated_at=current_timestamp,
        )
    )

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()


async def test_duplicate_organization_report_access_is_rejected(
    db_session: AsyncSession,
    seeded,
) -> None:
    current_timestamp = datetime.now(timezone.utc)
    db_session.add(
        OrganizationReportAccessORM(
            id="orgacc_duplicate_001",
            organization_id="org_sandbox_001",
            report_id="rpt_market_001",
            access_level="view",
            status="active",
            granted_at=current_timestamp,
            expires_at=None,
            granted_by_user_id="usr_admin_001",
            created_at=current_timestamp,
            updated_at=current_timestamp,
        )
    )

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()


async def test_duplicate_active_seat_assignment_is_rejected(
    db_session: AsyncSession,
    seeded,
) -> None:
    current_timestamp = datetime.now(timezone.utc)
    db_session.add(
        SeatAssignmentORM(
            id="seat_duplicate_001",
            organization_id="org_sandbox_001",
            seat_pool_id="seatpool_sandbox_standard",
            user_id="usr_member_001",
            status="active",
            assigned_at=current_timestamp,
            revoked_at=None,
            assigned_by_user_id="usr_admin_001",
            created_at=current_timestamp,
            updated_at=current_timestamp,
        )
    )

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()


async def test_membership_for_unknown_user_is_accepted_without_fk(
    db_session: AsyncSession,
    seeded,
) -> None:
    """After the Test_user1 cutover, local FK constraints to users are removed.

    Memberships no longer enforce cross-database referential integrity at the
    SQL level; the user-directory boundary handles this at application layer.
    """
    current_timestamp = datetime.now(timezone.utc)
    db_session.add(
        OrganizationMembershipORM(
            organization_id="org_sandbox_001",
            user_id="usr_missing_001",
            role="sandbox_reader",
            membership_status="active",
            joined_at=current_timestamp,
            created_at=current_timestamp,
            updated_at=current_timestamp,
        )
    )

    await db_session.commit()
    await db_session.rollback()


async def test_report_access_for_unknown_report_is_rejected(
    db_session: AsyncSession,
    seeded,
) -> None:
    current_timestamp = datetime.now(timezone.utc)
    db_session.add(
        OrganizationReportAccessORM(
            id="orgacc_unknown_report_001",
            organization_id="org_sandbox_001",
            report_id="rpt_missing_001",
            access_level="view",
            status="active",
            granted_at=current_timestamp,
            expires_at=None,
            granted_by_user_id="usr_admin_001",
            created_at=current_timestamp,
            updated_at=current_timestamp,
        )
    )

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()
