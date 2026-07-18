"""Coordinate Nucleus license/lifecycle projections in the sandbox."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.orm_models import (
    OrganizationORM,
    OrganizationOverviewORM,
    OrganizationSeatPoolORM,
    SeatAssignmentORM,
)
from app.domain.enums import (
    OrganizationStatus,
    SeatAssignmentStatus,
    SeatPoolStatus,
    SeatType,
)
from app.domain.nucleus_admin_models import (
    NucleusLicenseProjectionState,
    NucleusLifecycleProjectionState,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class NucleusAdministrationProjectionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _seat_pool(self, organization_id: str):
        return await self._session.scalar(
            select(OrganizationSeatPoolORM).where(
                OrganizationSeatPoolORM.organization_id == organization_id,
                OrganizationSeatPoolORM.seat_type == SeatType.STANDARD.value,
            )
        )

    async def get_license_projection(
        self, organization_id: str
    ) -> NucleusLicenseProjectionState | None:
        pool = await self._seat_pool(organization_id)
        overview = await self._session.get(
            OrganizationOverviewORM, organization_id
        )
        if pool is None or overview is None:
            return None
        active_assignments = int(
            await self._session.scalar(
                select(func.count())
                .select_from(SeatAssignmentORM)
                .where(
                    SeatAssignmentORM.organization_id == organization_id,
                    SeatAssignmentORM.seat_pool_id == pool.id,
                    SeatAssignmentORM.status
                    == SeatAssignmentStatus.ACTIVE.value,
                )
            )
            or 0
        )
        return NucleusLicenseProjectionState(
            seat_pool_id=pool.id,
            total_seats=pool.total_seats,
            starts_at=pool.starts_at,
            expires_at=pool.expires_at,
            seat_pool_status=pool.status,
            seat_pool_version=pool.version,
            active_assignments=active_assignments,
            renewal_date=overview.renewal_date,
            overview_version=overview.version,
        )

    async def update_license_projection_if_versions(
        self,
        *,
        organization_id: str,
        max_user_limit: int,
        license_start_date: datetime | None,
        license_end_date: datetime | None,
        expected_seat_pool_version: int,
        expected_overview_version: int,
    ) -> NucleusLicenseProjectionState | None:
        state = await self.get_license_projection(organization_id)
        if (
            state is None
            or state.seat_pool_version != expected_seat_pool_version
            or state.overview_version != expected_overview_version
            or state.active_assignments > max_user_limit
        ):
            return None
        now = _utcnow()
        pool_status = state.seat_pool_status
        if license_end_date is not None:
            end = license_end_date.replace(
                tzinfo=license_end_date.tzinfo or timezone.utc
            )
            if end < now:
                pool_status = SeatPoolStatus.EXPIRED.value
        pool_result = await self._session.execute(
            update(OrganizationSeatPoolORM)
            .where(
                OrganizationSeatPoolORM.id == state.seat_pool_id,
                OrganizationSeatPoolORM.version
                == expected_seat_pool_version,
            )
            .values(
                total_seats=max_user_limit,
                starts_at=license_start_date,
                expires_at=license_end_date,
                status=pool_status,
                version=expected_seat_pool_version + 1,
                updated_at=now,
            )
        )
        overview_result = await self._session.execute(
            update(OrganizationOverviewORM)
            .where(
                OrganizationOverviewORM.organization_id == organization_id,
                OrganizationOverviewORM.version == expected_overview_version,
            )
            .values(
                renewal_date=(
                    license_end_date.date()
                    if license_end_date is not None
                    else None
                ),
                version=expected_overview_version + 1,
                updated_at=now,
            )
        )
        if pool_result.rowcount != 1 or overview_result.rowcount != 1:
            await self._session.rollback()
            return None
        await self._session.commit()
        return await self.get_license_projection(organization_id)

    async def get_lifecycle_projection(
        self, organization_id: str
    ) -> NucleusLifecycleProjectionState | None:
        organization = await self._session.get(
            OrganizationORM, organization_id
        )
        pool = await self._seat_pool(organization_id)
        if organization is None or pool is None:
            return None
        return NucleusLifecycleProjectionState(
            organization_status=organization.status,
            organization_version=organization.version,
            seat_pool_id=pool.id,
            seat_pool_status=pool.status,
            seat_pool_version=pool.version,
        )

    async def update_lifecycle_projection_if_versions(
        self,
        *,
        organization_id: str,
        should_be_active: bool,
        license_end_date: datetime | None,
        expected_organization_version: int,
        expected_seat_pool_version: int,
    ) -> NucleusLifecycleProjectionState | None:
        state = await self.get_lifecycle_projection(organization_id)
        if (
            state is None
            or state.organization_version
            != expected_organization_version
            or state.seat_pool_version != expected_seat_pool_version
        ):
            return None
        now = _utcnow()
        expired = False
        if license_end_date is not None:
            expired = license_end_date.replace(
                tzinfo=license_end_date.tzinfo or timezone.utc
            ) < now
        target_org_status = (
            OrganizationStatus.ACTIVE.value
            if should_be_active and not expired
            else OrganizationStatus.SUSPENDED.value
        )
        target_pool_status = (
            SeatPoolStatus.EXPIRED.value
            if expired
            else (
                SeatPoolStatus.ACTIVE.value
                if should_be_active
                else SeatPoolStatus.SUSPENDED.value
            )
        )
        org_result = await self._session.execute(
            update(OrganizationORM)
            .where(
                OrganizationORM.id == organization_id,
                OrganizationORM.version == expected_organization_version,
            )
            .values(
                status=target_org_status,
                version=expected_organization_version + 1,
                updated_at=now,
            )
        )
        pool_result = await self._session.execute(
            update(OrganizationSeatPoolORM)
            .where(
                OrganizationSeatPoolORM.id == state.seat_pool_id,
                OrganizationSeatPoolORM.version
                == expected_seat_pool_version,
            )
            .values(
                status=target_pool_status,
                version=expected_seat_pool_version + 1,
                updated_at=now,
            )
        )
        if org_result.rowcount != 1 or pool_result.rowcount != 1:
            await self._session.rollback()
            return None
        await self._session.commit()
        return await self.get_lifecycle_projection(organization_id)
