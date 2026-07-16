"""Seat repository: reads seat pools and computes seat usage.

Seat usage is never stored. ``available_seats`` is always calculated as
``total_seats - active_assignments``.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.orm_models import OrganizationSeatPoolORM, SeatAssignmentORM
from app.domain.enums import SeatAssignmentStatus, SeatType
from app.domain.models import SeatSummary


class SeatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active_seat_user_ids(self, organization_id: str) -> set[str]:
        """Return the set of user ids holding an active seat in the org."""

        stmt = select(SeatAssignmentORM.user_id).where(
            SeatAssignmentORM.organization_id == organization_id,
            SeatAssignmentORM.status == SeatAssignmentStatus.ACTIVE.value,
        )
        result = await self._session.execute(stmt)
        return set(result.scalars().all())

    async def get_seat_summary(
        self, organization_id: str, seat_type: str = SeatType.STANDARD.value
    ) -> SeatSummary | None:
        """Return computed seat entitlement vs. usage for a seat type."""

        pool_stmt = select(OrganizationSeatPoolORM).where(
            OrganizationSeatPoolORM.organization_id == organization_id,
            OrganizationSeatPoolORM.seat_type == seat_type,
        )
        pool = (await self._session.execute(pool_stmt)).scalar_one_or_none()
        if pool is None:
            return None

        seated = await self._active_seated_user_ids(organization_id, pool.id)
        active = len(seated)
        return SeatSummary(
            organization_id=organization_id,
            seat_type=SeatType(pool.seat_type),
            total_seats=pool.total_seats,
            active_assignments=active,
            available_seats=pool.total_seats - active,
            seated_user_ids=tuple(sorted(seated)),
        )

    async def _active_seated_user_ids(
        self, organization_id: str, seat_pool_id: str
    ) -> set[str]:
        stmt = select(SeatAssignmentORM.user_id).where(
            SeatAssignmentORM.organization_id == organization_id,
            SeatAssignmentORM.seat_pool_id == seat_pool_id,
            SeatAssignmentORM.status == SeatAssignmentStatus.ACTIVE.value,
        )
        result = await self._session.execute(stmt)
        return set(result.scalars().all())

    async def count_active_assignments(self, organization_id: str) -> int:
        stmt = (
            select(func.count())
            .select_from(SeatAssignmentORM)
            .where(
                SeatAssignmentORM.organization_id == organization_id,
                SeatAssignmentORM.status == SeatAssignmentStatus.ACTIVE.value,
            )
        )
        return int(await self._session.scalar(stmt) or 0)
