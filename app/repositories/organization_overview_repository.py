"""Persistence mapping for the organization overview page."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.orm_models import OrganizationOverviewORM
from app.domain.enums import WorkspaceHealthStatus
from app.domain.models import (
    OrganizationOverview,
    OrganizationOverviewMetrics,
    OrganizationProfile,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OrganizationOverviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_for_profile(
        self,
        profile: OrganizationProfile,
    ) -> OrganizationOverview:
        row = await self._session.get(OrganizationOverviewORM, profile.id)
        if row is None:
            return OrganizationOverview(
                organization=profile,
                organization_type="organization",
                renewal_date=None,
                workspace_status=WorkspaceHealthStatus.UNKNOWN,
                metrics=OrganizationOverviewMetrics(
                    licensed_modules=0,
                    available_areas=0,
                    organization_logins=0,
                    workspace_health_percent=0,
                ),
                version=1,
                updated_at=profile.updated_at,
            )
        return self._to_domain(row, profile)

    async def update_organization_type_if_version(
        self,
        *,
        profile: OrganizationProfile,
        organization_type: str,
        expected_version: int,
    ) -> OrganizationOverview | None:
        statement = (
            update(OrganizationOverviewORM)
            .where(
                OrganizationOverviewORM.organization_id == profile.id,
                OrganizationOverviewORM.version == expected_version,
            )
            .values(
                organization_type=organization_type,
                version=expected_version + 1,
                updated_at=_utcnow(),
            )
        )
        result = await self._session.execute(statement)
        if result.rowcount != 1:
            await self._session.rollback()
            return None
        await self._session.commit()
        row = await self._session.get(OrganizationOverviewORM, profile.id)
        return self._to_domain(row, profile) if row is not None else None

    @staticmethod
    def _to_domain(
        row: OrganizationOverviewORM,
        profile: OrganizationProfile,
    ) -> OrganizationOverview:
        return OrganizationOverview(
            organization=profile,
            organization_type=row.organization_type,
            renewal_date=row.renewal_date,
            workspace_status=WorkspaceHealthStatus(row.workspace_status),
            metrics=OrganizationOverviewMetrics(
                licensed_modules=row.licensed_modules,
                available_areas=row.available_areas,
                organization_logins=row.organization_logins,
                workspace_health_percent=row.workspace_health_percent,
            ),
            version=row.version,
            updated_at=row.updated_at,
        )
