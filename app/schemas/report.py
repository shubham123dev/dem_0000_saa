"""Report catalog and organization report-access API schemas."""

from __future__ import annotations

from pydantic import BaseModel

from app.domain.enums import ReportAccessLevel, ReportAccessStatus, ReportStatus
from app.domain.models import Report, ReportAccessDecision, ReportWithAccess
from app.schemas.organization import OrganizationAccessOut


class ReportOut(BaseModel):
    """Public catalog-report representation."""

    id: str
    external_report_id: str
    title: str
    market_name: str | None = None
    status: ReportStatus

    @classmethod
    def from_domain(cls, report: Report) -> "ReportOut":
        return cls(
            id=report.id,
            external_report_id=report.external_report_id,
            title=report.title,
            market_name=report.market_name,
            status=report.status,
        )


class ReportWithAccessOut(BaseModel):
    """A catalog report annotated with this organization's access."""

    report: ReportOut
    has_access: bool
    access_level: ReportAccessLevel | None = None
    access_status: ReportAccessStatus | None = None

    @classmethod
    def from_domain(cls, item: ReportWithAccess) -> "ReportWithAccessOut":
        return cls(
            report=ReportOut.from_domain(item.report),
            has_access=item.has_access,
            access_level=item.access_level,
            access_status=item.access_status,
        )


class OrganizationReportsResponse(BaseModel):
    """Response body for the list-organization-reports endpoint."""

    organization_id: str
    reports: list[ReportWithAccessOut]
    access: OrganizationAccessOut


class ReportAccessResponse(BaseModel):
    """Response body for the check-organization-report-access endpoint."""

    organization_id: str
    report_id: str
    has_access: bool
    access_level: ReportAccessLevel | None = None
    access_status: ReportAccessStatus | None = None
    access: OrganizationAccessOut

    @classmethod
    def from_decision(
        cls, decision: ReportAccessDecision, access: OrganizationAccessOut
    ) -> "ReportAccessResponse":
        return cls(
            organization_id=decision.organization_id,
            report_id=decision.report_id,
            has_access=decision.has_access,
            access_level=decision.access_level,
            access_status=decision.access_status,
            access=access,
        )
