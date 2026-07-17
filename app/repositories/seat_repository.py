from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.orm_models import (
    OrganizationMembershipORM,
    OrganizationSeatPoolORM,
    SeatAssignmentORM,
)
from app.domain.effective_period import is_reference_time_within_effective_period
from app.domain.enums import (
    MembershipStatus,
    SeatAssignmentStatus,
    SeatPoolStatus,
    SeatType,
)
from app.domain.models import SeatSummary


class SeatRepository:
    def __init__(self, database_session: AsyncSession) -> None:
        self._database_session = database_session

    async def get_active_seat_user_ids(
        self,
        organization_id: str,
        reference_time_utc: datetime | None = None,
    ) -> set[str]:
        evaluated_reference_time_utc = reference_time_utc or datetime.now(timezone.utc)
        seat_pool_statement = select(OrganizationSeatPoolORM).where(
            OrganizationSeatPoolORM.organization_id == organization_id,
            OrganizationSeatPoolORM.status == SeatPoolStatus.ACTIVE.value,
        )
        seat_pool_result = await self._database_session.execute(seat_pool_statement)
        valid_seat_pool_ids = {
            seat_pool_record.id
            for seat_pool_record in seat_pool_result.scalars().all()
            if is_reference_time_within_effective_period(
                effective_period_start=seat_pool_record.starts_at,
                effective_period_end=seat_pool_record.expires_at,
                reference_time_utc=evaluated_reference_time_utc,
            )
        }
        if not valid_seat_pool_ids:
            return set()

        active_seat_assignment_statement = (
            select(SeatAssignmentORM.user_id)
            .join(
                OrganizationMembershipORM,
                (OrganizationMembershipORM.organization_id == organization_id)
                & (OrganizationMembershipORM.user_id == SeatAssignmentORM.user_id),
            )
            .where(
                SeatAssignmentORM.organization_id == organization_id,
                SeatAssignmentORM.seat_pool_id.in_(valid_seat_pool_ids),
                SeatAssignmentORM.status == SeatAssignmentStatus.ACTIVE.value,
                OrganizationMembershipORM.membership_status
                == MembershipStatus.ACTIVE.value,
            )
        )
        active_seat_assignment_result = await self._database_session.execute(
            active_seat_assignment_statement
        )
        return set(active_seat_assignment_result.scalars().all())

    async def get_seat_summary(
        self,
        organization_id: str,
        seat_type: str = SeatType.STANDARD.value,
        reference_time_utc: datetime | None = None,
    ) -> SeatSummary | None:
        evaluated_reference_time_utc = reference_time_utc or datetime.now(timezone.utc)
        seat_pool_statement = select(OrganizationSeatPoolORM).where(
            OrganizationSeatPoolORM.organization_id == organization_id,
            OrganizationSeatPoolORM.seat_type == seat_type,
        )
        seat_pool_result = await self._database_session.execute(seat_pool_statement)
        seat_pool_record = seat_pool_result.scalar_one_or_none()
        if seat_pool_record is None:
            return None

        seat_pool_is_usable = (
            seat_pool_record.status == SeatPoolStatus.ACTIVE.value
            and is_reference_time_within_effective_period(
                effective_period_start=seat_pool_record.starts_at,
                effective_period_end=seat_pool_record.expires_at,
                reference_time_utc=evaluated_reference_time_utc,
            )
        )
        if not seat_pool_is_usable:
            return None

        seated_user_ids = await self._get_active_member_seat_user_ids(
            organization_id=organization_id,
            seat_pool_id=seat_pool_record.id,
        )
        active_assignment_count = len(seated_user_ids)
        non_negative_total_seats = max(seat_pool_record.total_seats, 0)
        available_seat_count = max(
            non_negative_total_seats - active_assignment_count,
            0,
        )
        return SeatSummary(
            organization_id=organization_id,
            seat_type=SeatType(seat_pool_record.seat_type),
            total_seats=non_negative_total_seats,
            active_assignments=active_assignment_count,
            available_seats=available_seat_count,
            seated_user_ids=tuple(sorted(seated_user_ids)),
        )

    async def _get_active_member_seat_user_ids(
        self,
        *,
        organization_id: str,
        seat_pool_id: str,
    ) -> set[str]:
        active_member_seat_statement = (
            select(SeatAssignmentORM.user_id)
            .join(
                OrganizationMembershipORM,
                (OrganizationMembershipORM.organization_id == organization_id)
                & (OrganizationMembershipORM.user_id == SeatAssignmentORM.user_id),
            )
            .where(
                SeatAssignmentORM.organization_id == organization_id,
                SeatAssignmentORM.seat_pool_id == seat_pool_id,
                SeatAssignmentORM.status == SeatAssignmentStatus.ACTIVE.value,
                OrganizationMembershipORM.membership_status
                == MembershipStatus.ACTIVE.value,
            )
        )
        active_member_seat_result = await self._database_session.execute(
            active_member_seat_statement
        )
        return set(active_member_seat_result.scalars().all())

    async def count_active_assignments(self, organization_id: str) -> int:
        active_assignment_count_statement = (
            select(func.count())
            .select_from(SeatAssignmentORM)
            .where(
                SeatAssignmentORM.organization_id == organization_id,
                SeatAssignmentORM.status == SeatAssignmentStatus.ACTIVE.value,
            )
        )
        active_assignment_count = await self._database_session.scalar(
            active_assignment_count_statement
        )
        return int(active_assignment_count or 0)
