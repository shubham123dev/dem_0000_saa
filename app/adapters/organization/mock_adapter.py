from __future__ import annotations

from app.domain.models import (
    OrganizationMember,
    OrganizationProfile,
    ReportAccessDecision,
    ReportWithAccess,
    SeatSummary,
)
from app.mock_api.service import MockOrganizationApi


class MockOrganizationApiAdapter:
    def __init__(self, mock_api: MockOrganizationApi) -> None:
        self._api = mock_api

    async def get_profile(self, organization_id: str) -> OrganizationProfile:
        return await self._api.get_organization(organization_id)

    async def list_members(self, organization_id: str) -> list[OrganizationMember]:
        return await self._api.list_users(organization_id)

    async def get_seat_summary(self, organization_id: str) -> SeatSummary:
        return await self._api.get_seat_summary(organization_id)

    async def list_reports(self, organization_id: str) -> list[ReportWithAccess]:
        return await self._api.list_reports(organization_id)

    async def check_report_access(
        self,
        organization_id: str,
        report_id: str,
    ) -> ReportAccessDecision:
        return await self._api.check_report_access(organization_id, report_id)

    async def update_contact_email(
        self,
        organization_id: str,
        contact_email: str,
    ) -> OrganizationProfile:
        return await self._api.update_contact_email(organization_id, contact_email)


MockOrganizationAdapter = MockOrganizationApiAdapter
