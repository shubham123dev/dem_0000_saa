from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ReportNotFoundError
from app.db.orm_models import OrganizationReportAccessORM, ReportORM
from app.domain.effective_period import is_reference_time_within_effective_period
from app.domain.enums import (
    ReportAccessLevel,
    ReportAccessStatus,
    ReportStatus,
)
from app.domain.models import Report, ReportAccessDecision


class ReportRepository:
    def __init__(self, database_session: AsyncSession) -> None:
        self._database_session = database_session

    async def list_active_reports(self) -> list[Report]:
        active_reports_statement = (
            select(ReportORM)
            .where(ReportORM.status == ReportStatus.ACTIVE.value)
            .order_by(ReportORM.id.asc())
        )
        active_reports_result = await self._database_session.execute(
            active_reports_statement
        )
        return [
            self._convert_report_record_to_domain_model(report_record)
            for report_record in active_reports_result.scalars().all()
        ]

    async def get_current_access_map(
        self,
        organization_id: str,
        reference_time_utc: datetime | None = None,
    ) -> dict[str, tuple[ReportAccessLevel, ReportAccessStatus]]:
        evaluated_reference_time_utc = reference_time_utc or datetime.now(timezone.utc)
        organization_access_statement = select(OrganizationReportAccessORM).where(
            OrganizationReportAccessORM.organization_id == organization_id,
            OrganizationReportAccessORM.status == ReportAccessStatus.ACTIVE.value,
        )
        organization_access_result = await self._database_session.execute(
            organization_access_statement
        )
        current_access_by_report_id: dict[
            str,
            tuple[ReportAccessLevel, ReportAccessStatus],
        ] = {}

        for organization_report_access_record in organization_access_result.scalars().all():
            access_is_current = is_reference_time_within_effective_period(
                effective_period_start=None,
                effective_period_end=organization_report_access_record.expires_at,
                reference_time_utc=evaluated_reference_time_utc,
            )
            if access_is_current:
                current_access_by_report_id[organization_report_access_record.report_id] = (
                    ReportAccessLevel(organization_report_access_record.access_level),
                    ReportAccessStatus.ACTIVE,
                )

        return current_access_by_report_id

    async def require_active_report(self, report_id: str) -> Report:
        report_record = await self._database_session.get(ReportORM, report_id)
        if report_record is None or report_record.status != ReportStatus.ACTIVE.value:
            raise ReportNotFoundError()
        return self._convert_report_record_to_domain_model(report_record)

    async def get_access_decision(
        self,
        organization_id: str,
        report_id: str,
        reference_time_utc: datetime | None = None,
    ) -> ReportAccessDecision:
        await self.require_active_report(report_id)
        evaluated_reference_time_utc = reference_time_utc or datetime.now(timezone.utc)
        organization_report_access_statement = select(
            OrganizationReportAccessORM
        ).where(
            OrganizationReportAccessORM.organization_id == organization_id,
            OrganizationReportAccessORM.report_id == report_id,
        )
        organization_report_access_result = await self._database_session.execute(
            organization_report_access_statement
        )
        organization_report_access_record = (
            organization_report_access_result.scalar_one_or_none()
        )

        if organization_report_access_record is None:
            return ReportAccessDecision(
                organization_id=organization_id,
                report_id=report_id,
                has_access=False,
                access_level=None,
                access_status=None,
            )

        persisted_access_status = ReportAccessStatus(
            organization_report_access_record.status
        )
        access_is_current = is_reference_time_within_effective_period(
            effective_period_start=None,
            effective_period_end=organization_report_access_record.expires_at,
            reference_time_utc=evaluated_reference_time_utc,
        )
        effective_access_status = persisted_access_status
        if persisted_access_status == ReportAccessStatus.ACTIVE and not access_is_current:
            effective_access_status = ReportAccessStatus.EXPIRED

        return ReportAccessDecision(
            organization_id=organization_id,
            report_id=report_id,
            has_access=effective_access_status == ReportAccessStatus.ACTIVE,
            access_level=ReportAccessLevel(
                organization_report_access_record.access_level
            ),
            access_status=effective_access_status,
        )

    @staticmethod
    def _convert_report_record_to_domain_model(report_record: ReportORM) -> Report:
        return Report(
            id=report_record.id,
            external_report_id=report_record.external_report_id,
            title=report_record.title,
            market_name=report_record.market_name,
            status=ReportStatus(report_record.status),
        )
