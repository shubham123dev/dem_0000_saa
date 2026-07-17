from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.domain.models import (
    OrganizationMember,
    OrganizationOverview,
    OrganizationProfile,
    ReportAccessDecision,
    ReportWithAccess,
    SeatSummary,
)


@runtime_checkable
class OrganizationApiGateway(Protocol):
    async def get_profile(self, organization_id: str) -> OrganizationProfile:
        ...

    async def get_overview(self, organization_id: str) -> OrganizationOverview:
        ...

    async def list_members(self, organization_id: str) -> list[OrganizationMember]:
        ...

    async def get_seat_summary(self, organization_id: str) -> SeatSummary:
        ...

    async def list_reports(self, organization_id: str) -> list[ReportWithAccess]:
        ...

    async def check_report_access(
        self,
        organization_id: str,
        report_id: str,
    ) -> ReportAccessDecision:
        ...

    async def update_contact_email(
        self,
        organization_id: str,
        contact_email: str,
    ) -> OrganizationProfile:
        ...

    async def update_contact_email_if_version(
        self,
        organization_id: str,
        contact_email: str,
        expected_version: int,
    ) -> OrganizationProfile | None:
        ...


OrganizationGateway = OrganizationApiGateway
OrganizationAdapter = OrganizationApiGateway
