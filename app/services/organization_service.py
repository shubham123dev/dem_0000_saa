"""Organization service for the Step 0 read-only workplace tools."""

from __future__ import annotations

from app.adapters.organization.contract import OrganizationApiGateway
from app.core.errors import OrganizationSuspendedError, ProductionAccessBlockedError
from app.domain.enums import Environment, OrganizationStatus, Permission
from app.domain.models import (
    AuditEvent,
    OrganizationMember,
    OrganizationProfile,
    ReportAccessDecision,
    ReportWithAccess,
    SeatSummary,
    User,
)
from app.permissions.permission_service import PermissionService
from app.repositories.audit_repository import AuditRepository
from app.schemas.permission import AccessContext


class OrganizationService:
    def __init__(
        self,
        *,
        organization_gateway: OrganizationApiGateway,
        permission_service: PermissionService,
        audit_repository: AuditRepository,
    ) -> None:
        self._organization_gateway = organization_gateway
        self._permission_service = permission_service
        self._audit_repository = audit_repository

    async def _resolve_organization_and_authorize_user(
        self,
        *,
        user: User,
        organization_id: str,
        required_permission: str,
    ) -> tuple[OrganizationProfile, AccessContext]:
        organization_profile = await self._organization_gateway.get_profile(
            organization_id
        )

        if organization_profile.environment != Environment.SANDBOX:
            raise ProductionAccessBlockedError()

        if organization_profile.status != OrganizationStatus.ACTIVE:
            raise OrganizationSuspendedError()

        access_context = await self._permission_service.authorize(
            user=user,
            organization_id=organization_id,
            required_permission=required_permission,
        )
        return organization_profile, access_context

    async def read_profile(
        self,
        *,
        user: User,
        organization_id: str,
    ) -> tuple[OrganizationProfile, AccessContext]:
        required_permission = Permission.ORGANIZATION_PROFILE_READ.value
        organization_profile, access_context = (
            await self._resolve_organization_and_authorize_user(
                user=user,
                organization_id=organization_id,
                required_permission=required_permission,
            )
        )
        await self._audit_repository.append(
            actor_user_id=user.id,
            organization_id=organization_id,
            event_type="organization.profile.read",
            operation="read",
            outcome="success",
            resource_type="organization",
            resource_id=organization_id,
            details={
                "permission": required_permission,
                "tool": "get_organization_profile",
            },
        )
        return organization_profile, access_context

    async def list_users(
        self,
        *,
        user: User,
        organization_id: str,
    ) -> tuple[list[OrganizationMember], AccessContext]:
        required_permission = Permission.ORGANIZATION_USERS_READ.value
        _, access_context = await self._resolve_organization_and_authorize_user(
            user=user,
            organization_id=organization_id,
            required_permission=required_permission,
        )
        organization_members = await self._organization_gateway.list_members(
            organization_id
        )
        await self._audit_repository.append(
            actor_user_id=user.id,
            organization_id=organization_id,
            event_type="organization.users.read",
            operation="read",
            outcome="success",
            resource_type="organization_users",
            resource_id=organization_id,
            details={
                "permission": required_permission,
                "tool": "list_organization_users",
                "count": len(organization_members),
            },
        )
        return organization_members, access_context

    async def get_seat_summary(
        self,
        *,
        user: User,
        organization_id: str,
    ) -> tuple[SeatSummary, AccessContext]:
        required_permission = Permission.ORGANIZATION_SEATS_READ.value
        _, access_context = await self._resolve_organization_and_authorize_user(
            user=user,
            organization_id=organization_id,
            required_permission=required_permission,
        )
        seat_summary = await self._organization_gateway.get_seat_summary(
            organization_id
        )
        await self._audit_repository.append(
            actor_user_id=user.id,
            organization_id=organization_id,
            event_type="organization.seats.read",
            operation="read",
            outcome="success",
            resource_type="organization_seats",
            resource_id=organization_id,
            details={
                "permission": required_permission,
                "tool": "get_organization_seat_summary",
                "total_seats": seat_summary.total_seats,
                "active_assignments": seat_summary.active_assignments,
            },
        )
        return seat_summary, access_context

    async def list_reports(
        self,
        *,
        user: User,
        organization_id: str,
    ) -> tuple[list[ReportWithAccess], AccessContext]:
        required_permission = Permission.ORGANIZATION_REPORTS_READ.value
        _, access_context = await self._resolve_organization_and_authorize_user(
            user=user,
            organization_id=organization_id,
            required_permission=required_permission,
        )
        organization_reports = await self._organization_gateway.list_reports(
            organization_id
        )
        await self._audit_repository.append(
            actor_user_id=user.id,
            organization_id=organization_id,
            event_type="organization.reports.read",
            operation="read",
            outcome="success",
            resource_type="organization_reports",
            resource_id=organization_id,
            details={
                "permission": required_permission,
                "tool": "list_organization_reports",
                "count": len(organization_reports),
                "accessible": sum(
                    1
                    for organization_report in organization_reports
                    if organization_report.has_access
                ),
            },
        )
        return organization_reports, access_context

    async def check_report_access(
        self,
        *,
        user: User,
        organization_id: str,
        report_id: str,
    ) -> tuple[ReportAccessDecision, AccessContext]:
        required_permission = Permission.ORGANIZATION_REPORTS_READ.value
        _, access_context = await self._resolve_organization_and_authorize_user(
            user=user,
            organization_id=organization_id,
            required_permission=required_permission,
        )
        report_access_decision = (
            await self._organization_gateway.check_report_access(
                organization_id,
                report_id,
            )
        )
        await self._audit_repository.append(
            actor_user_id=user.id,
            organization_id=organization_id,
            event_type="organization.reports.access_check",
            operation="read",
            outcome="success",
            resource_type="report",
            resource_id=report_id,
            details={
                "permission": required_permission,
                "tool": "check_organization_report_access",
                "has_access": report_access_decision.has_access,
            },
        )
        return report_access_decision, access_context

    async def list_audit_events(
        self,
        *,
        user: User,
        organization_id: str,
    ) -> tuple[list[AuditEvent], AccessContext]:
        required_permission = Permission.AUDIT_READ.value
        _, access_context = await self._resolve_organization_and_authorize_user(
            user=user,
            organization_id=organization_id,
            required_permission=required_permission,
        )
        audit_events = await self._audit_repository.list_for_organization(
            organization_id
        )
        return audit_events, access_context
