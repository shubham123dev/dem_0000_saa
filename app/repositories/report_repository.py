"""Report repository: reads the report catalog and organization access rows."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.orm_models import OrganizationReportAccessORM, ReportORM
from app.domain.enums import (
    ReportAccessLevel,
    ReportAccessStatus,
    ReportStatus,
)
from app.domain.models import Report, ReportAccessDecision


class ReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_reports(self) -> list[Report]:
        """Return the full mock report catalog, ordered deterministically."""

        stmt = select(ReportORM).order_by(ReportORM.id.asc())
        result = await self._session.execute(stmt)
        return [self._to_report(row) for row in result.scalars().all()]

    async def get_active_access_map(
        self, organization_id: str
    ) -> dict[str, tuple[ReportAccessLevel, ReportAccessStatus]]:
        """Map report_id -> (access_level, status) for *active* access rows."""

        stmt = select(OrganizationReportAccessORM).where(
            OrganizationReportAccessORM.organization_id == organization_id,
            OrganizationReportAccessORM.status == ReportAccessStatus.ACTIVE.value,
        )
        result = await self._session.execute(stmt)
        return {
            row.report_id: (
                ReportAccessLevel(row.access_level),
                ReportAccessStatus(row.status),
            )
            for row in result.scalars().all()
        }

    async def report_exists(self, report_id: str) -> bool:
        return (await self._session.get(ReportORM, report_id)) is not None

    async def get_access_decision(
        self, organization_id: str, report_id: str
    ) -> ReportAccessDecision:
        """Resolve the organization's access decision for a single report."""

        stmt = select(OrganizationReportAccessORM).where(
            OrganizationReportAccessORM.organization_id == organization_id,
            OrganizationReportAccessORM.report_id == report_id,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return ReportAccessDecision(
                organization_id=organization_id,
                report_id=report_id,
                has_access=False,
                access_level=None,
                access_status=None,
            )
        status = ReportAccessStatus(row.status)
        return ReportAccessDecision(
            organization_id=organization_id,
            report_id=report_id,
            has_access=status == ReportAccessStatus.ACTIVE,
            access_level=ReportAccessLevel(row.access_level),
            access_status=status,
        )

    @staticmethod
    def _to_report(row: ReportORM) -> Report:
        return Report(
            id=row.id,
            external_report_id=row.external_report_id,
            title=row.title,
            market_name=row.market_name,
            status=ReportStatus(row.status),
        )
