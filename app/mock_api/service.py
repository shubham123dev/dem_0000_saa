from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import OrganizationNotFoundError
from app.domain.enums import MembershipStatus, SeatType, UserStatus
from app.domain.models import (
    AuditEvent,
    OrganizationMember,
    OrganizationProfile,
    ReportAccessDecision,
    ReportWithAccess,
    SeatSummary,
)
from app.repositories.audit_repository import AuditRepository
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.report_repository import ReportRepository
from app.repositories.seat_repository import SeatRepository
from app.repositories.user_repository import UserRepository


class MockOrganizationApi:
    def __init__(self, database_session: AsyncSession) -> None:
        self._organization_repository = OrganizationRepository(database_session)
        self._user_repository = UserRepository(database_session)
        self._seat_repository = SeatRepository(database_session)
        self._report_repository = ReportRepository(database_session)
        self._audit_repository = AuditRepository(database_session)

    async def _require_organization_profile(
        self,
        organization_id: str,
    ) -> OrganizationProfile:
        organization_profile = await self._organization_repository.get_profile(
            organization_id
        )
        if organization_profile is None:
            raise OrganizationNotFoundError()
        return organization_profile

    async def get_organization(self, organization_id: str) -> OrganizationProfile:
        return await self._require_organization_profile(organization_id)

    async def update_contact_email(
        self,
        organization_id: str,
        contact_email: str,
    ) -> OrganizationProfile:
        await self._require_organization_profile(organization_id)
        organization_profile = await self._organization_repository.update_contact_email(
            organization_id,
            contact_email,
        )
        if organization_profile is None:
            raise OrganizationNotFoundError()
        return organization_profile

    async def list_users(self, organization_id: str) -> list[OrganizationMember]:
        await self._require_organization_profile(organization_id)
        active_seat_user_ids = (
            await self._seat_repository.get_active_seat_user_ids(organization_id)
        )
        organization_members: list[OrganizationMember] = []

        organization_membership_records = (
            await self._user_repository.list_memberships(organization_id)
        )
        for user_record, membership_record in organization_membership_records:
            organization_members.append(
                OrganizationMember(
                    user_id=user_record.id,
                    display_name=user_record.display_name,
                    email=user_record.email,
                    user_status=UserStatus(user_record.status),
                    role=membership_record.role,
                    membership_status=MembershipStatus(
                        membership_record.membership_status
                    ),
                    has_active_seat=user_record.id in active_seat_user_ids,
                    joined_at=membership_record.joined_at,
                )
            )

        return organization_members

    async def get_seat_summary(self, organization_id: str) -> SeatSummary:
        await self._require_organization_profile(organization_id)
        seat_summary = await self._seat_repository.get_seat_summary(organization_id)
        if seat_summary is not None:
            return seat_summary

        return SeatSummary(
            organization_id=organization_id,
            seat_type=SeatType.STANDARD,
            total_seats=0,
            active_assignments=0,
            available_seats=0,
            seated_user_ids=(),
        )

    async def list_reports(self, organization_id: str) -> list[ReportWithAccess]:
        await self._require_organization_profile(organization_id)
        current_access_by_report_id = (
            await self._report_repository.get_current_access_map(organization_id)
        )
        active_report_catalog = await self._report_repository.list_active_reports()
        organization_reports: list[ReportWithAccess] = []

        for active_report in active_report_catalog:
            current_report_access = current_access_by_report_id.get(active_report.id)
            organization_reports.append(
                ReportWithAccess(
                    report=active_report,
                    has_access=current_report_access is not None,
                    access_level=(
                        current_report_access[0]
                        if current_report_access is not None
                        else None
                    ),
                    access_status=(
                        current_report_access[1]
                        if current_report_access is not None
                        else None
                    ),
                )
            )

        return organization_reports

    async def check_report_access(
        self,
        organization_id: str,
        report_id: str,
    ) -> ReportAccessDecision:
        await self._require_organization_profile(organization_id)
        return await self._report_repository.get_access_decision(
            organization_id,
            report_id,
        )

    async def get_audit_log(self, organization_id: str) -> list[AuditEvent]:
        await self._require_organization_profile(organization_id)
        return await self._audit_repository.list_for_organization(organization_id)
