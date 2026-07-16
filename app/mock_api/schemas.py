"""Wire-format response schemas for the raw mock external API.

These deliberately omit any workplace access-context: the mock API represents an
external system of record, not the Workplace Agent. Access decisions are made by
the agent layer, not here.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.domain.enums import ReportAccessLevel, ReportAccessStatus
from app.schemas.audit import AuditEventOut
from app.schemas.organization import OrganizationOut
from app.schemas.report import ReportWithAccessOut
from app.schemas.seat import SeatSummaryOut
from app.schemas.user import OrganizationMemberOut


class MockUsersResponse(BaseModel):
    organization_id: str
    users: list[OrganizationMemberOut]


class MockSeatsResponse(BaseModel):
    organization_id: str
    seats: SeatSummaryOut


class MockReportsResponse(BaseModel):
    organization_id: str
    reports: list[ReportWithAccessOut]


class MockReportAccessResponse(BaseModel):
    organization_id: str
    report_id: str
    has_access: bool
    access_level: ReportAccessLevel | None = None
    access_status: ReportAccessStatus | None = None


class MockAuditLogResponse(BaseModel):
    organization_id: str
    events: list[AuditEventOut]


__all__ = [
    "OrganizationOut",
    "MockUsersResponse",
    "MockSeatsResponse",
    "MockReportsResponse",
    "MockReportAccessResponse",
    "MockAuditLogResponse",
]
