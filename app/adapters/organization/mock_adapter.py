from __future__ import annotations

from app.domain.models import (
    OrganizationMember,
    OrganizationOverview,
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

    async def get_overview(self, organization_id: str) -> OrganizationOverview:
        return await self._api.get_overview(organization_id)

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

    async def update_contact_email_if_version(
        self,
        organization_id: str,
        contact_email: str | None,
        expected_version: int,
    ) -> OrganizationProfile | None:
        return await self._api.update_contact_email_if_version(
            organization_id,
            contact_email,
            expected_version,
        )

    async def update_display_name_if_version(
        self,
        organization_id: str,
        display_name: str,
        expected_version: int,
    ) -> OrganizationProfile | None:
        return await self._api.update_display_name_if_version(
            organization_id,
            display_name,
            expected_version,
        )

    async def update_organization_type_if_version(
        self,
        organization_id: str,
        organization_type: str,
        expected_version: int,
    ) -> OrganizationOverview | None:
        return await self._api.update_organization_type_if_version(
            organization_id,
            organization_type,
            expected_version,
        )


MockOrganizationAdapter = MockOrganizationApiAdapter
