"""In-process mock organization backend.

``MockOrganizationApi`` is the single implementation shared by two callers:

* the ``/mock-api/v1`` HTTP routes (the raw external mock API surface), and
* ``MockOrganizationApiAdapter`` (the in-process seam the Workplace Agent uses).

It returns framework-agnostic **domain models** and reads only through
repositories. It performs NO workplace permission enforcement — it simulates an
external system of record (later the real Nucleus organization API). Backend-
owned permission/seat/access decisions live in the Workplace Agent layer.
"""

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
    """Mock backend for organization, user, seat, report-access, and audit data."""

    def __init__(self, session: AsyncSession) -> None:
        self._organizations = OrganizationRepository(session)
        self._users = UserRepository(session)
        self._seats = SeatRepository(session)
        self._reports = ReportRepository(session)
        self._audit = AuditRepository(session)

    async def _require_profile(self, organization_id: str) -> OrganizationProfile:
        profile = await self._organizations.get_profile(organization_id)
        if profile is None:
            raise OrganizationNotFoundError()
        return profile

    async def get_organization(self, organization_id: str) -> OrganizationProfile:
        return await self._require_profile(organization_id)

    async def list_users(self, organization_id: str) -> list[OrganizationMember]:
        await self._require_profile(organization_id)
        seated = await self._seats.get_active_seat_user_ids(organization_id)
        members: list[OrganizationMember] = []
        for user, membership in await self._users.list_memberships(organization_id):
            members.append(
                OrganizationMember(
                    user_id=user.id,
                    display_name=user.display_name,
                    email=user.email,
                    user_status=UserStatus(user.status),
                    role=membership.role,
                    membership_status=MembershipStatus(membership.membership_status),
                    has_active_seat=user.id in seated,
                    joined_at=membership.joined_at,
                )
            )
        return members

    async def get_seat_summary(self, organization_id: str) -> SeatSummary:
        await self._require_profile(organization_id)
        summary = await self._seats.get_seat_summary(organization_id)
        if summary is None:
            # No licensed pool -> zero entitlement (still a valid, empty summary).
            return SeatSummary(
                organization_id=organization_id,
                seat_type=SeatType.STANDARD,
                total_seats=0,
                active_assignments=0,
                available_seats=0,
                seated_user_ids=(),
            )
        return summary

    async def list_reports(self, organization_id: str) -> list[ReportWithAccess]:
        await self._require_profile(organization_id)
        access_map = await self._reports.get_active_access_map(organization_id)
        catalog = await self._reports.list_reports()
        items: list[ReportWithAccess] = []
        for report in catalog:
            access = access_map.get(report.id)
            level = access[0] if access else None
            status = access[1] if access else None
            items.append(
                ReportWithAccess(
                    report=report,
                    has_access=access is not None,
                    access_level=level,
                    access_status=status,
                )
            )
        return items

    async def check_report_access(
        self, organization_id: str, report_id: str
    ) -> ReportAccessDecision:
        await self._require_profile(organization_id)
        return await self._reports.get_access_decision(organization_id, report_id)

    async def get_audit_log(self, organization_id: str) -> list[AuditEvent]:
        await self._require_profile(organization_id)
        return await self._audit.list_for_organization(organization_id)
