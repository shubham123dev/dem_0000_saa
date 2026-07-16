"""Organization service: orchestrates the Step 0 read-only tools.

Every read tool follows the same backend-owned pipeline:

    resolve organization (via the OrganizationApiGateway contract)
    → enforce sandbox-only environment (block production)
    → authorize user (active membership + required permission)
    → fetch data (via the gateway)
    → append an append-only audit event
    → return domain data + access context

The service depends only on the ``OrganizationApiGateway`` adapter contract and
the permission/audit collaborators — never on the ORM directly. Access is
always decided by backend data, never by any model, prompt, or request text.
"""

from __future__ import annotations

from app.adapters.organization.contract import OrganizationApiGateway
from app.core.errors import ProductionAccessBlockedError
from app.domain.enums import Environment, Permission
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
        self._gateway = organization_gateway
        self._permissions = permission_service
        self._audit = audit_repository

    async def _resolve_and_authorize(
        self, *, user: User, organization_id: str, required_permission: str
    ) -> tuple[OrganizationProfile, AccessContext]:
        """Shared prelude: resolve org, block production, authorize the user."""

        profile = await self._gateway.get_profile(organization_id)

        if profile.environment != Environment.SANDBOX:
            raise ProductionAccessBlockedError()

        # Administrative reads require an active membership and permission.
        # They deliberately do not require a licensed seat.
        access = await self._permissions.authorize(
            user=user,
            organization_id=organization_id,
            required_permission=required_permission,
        )
        return profile, access

    async def read_profile(
        self, *, user: User, organization_id: str
    ) -> tuple[OrganizationProfile, AccessContext]:
        """Tool: ``get_organization_profile``."""

        required = Permission.ORGANIZATION_PROFILE_READ.value
        profile, access = await self._resolve_and_authorize(
            user=user, organization_id=organization_id, required_permission=required
        )
        await self._audit.append(
            actor_user_id=user.id,
            organization_id=organization_id,
            event_type="organization.profile.read",
            operation="read",
            outcome="success",
            resource_type="organization",
            resource_id=organization_id,
            details={"permission": required, "tool": "get_organization_profile"},
        )
        return profile, access

    async def list_users(
        self, *, user: User, organization_id: str
    ) -> tuple[list[OrganizationMember], AccessContext]:
        """Tool: ``list_organization_users``."""

        required = Permission.ORGANIZATION_USERS_READ.value
        _, access = await self._resolve_and_authorize(
            user=user, organization_id=organization_id, required_permission=required
        )
        members = await self._gateway.list_members(organization_id)
        await self._audit.append(
            actor_user_id=user.id,
            organization_id=organization_id,
            event_type="organization.users.read",
            operation="read",
            outcome="success",
            resource_type="organization_users",
            resource_id=organization_id,
            details={
                "permission": required,
                "tool": "list_organization_users",
                "count": len(members),
            },
        )
        return members, access

    async def get_seat_summary(
        self, *, user: User, organization_id: str
    ) -> tuple[SeatSummary, AccessContext]:
        """Tool: ``get_organization_seat_summary``."""

        required = Permission.ORGANIZATION_SEATS_READ.value
        _, access = await self._resolve_and_authorize(
            user=user, organization_id=organization_id, required_permission=required
        )
        summary = await self._gateway.get_seat_summary(organization_id)
        await self._audit.append(
            actor_user_id=user.id,
            organization_id=organization_id,
            event_type="organization.seats.read",
            operation="read",
            outcome="success",
            resource_type="organization_seats",
            resource_id=organization_id,
            details={
                "permission": required,
                "tool": "get_organization_seat_summary",
                "total_seats": summary.total_seats,
                "active_assignments": summary.active_assignments,
            },
        )
        return summary, access

    async def list_reports(
        self, *, user: User, organization_id: str
    ) -> tuple[list[ReportWithAccess], AccessContext]:
        """Tool: ``list_organization_reports``."""

        required = Permission.ORGANIZATION_REPORTS_READ.value
        _, access = await self._resolve_and_authorize(
            user=user, organization_id=organization_id, required_permission=required
        )
        reports = await self._gateway.list_reports(organization_id)
        await self._audit.append(
            actor_user_id=user.id,
            organization_id=organization_id,
            event_type="organization.reports.read",
            operation="read",
            outcome="success",
            resource_type="organization_reports",
            resource_id=organization_id,
            details={
                "permission": required,
                "tool": "list_organization_reports",
                "count": len(reports),
                "accessible": sum(1 for r in reports if r.has_access),
            },
        )
        return reports, access

    async def check_report_access(
        self, *, user: User, organization_id: str, report_id: str
    ) -> tuple[ReportAccessDecision, AccessContext]:
        """Tool: ``check_organization_report_access``."""

        required = Permission.ORGANIZATION_REPORTS_READ.value
        _, access = await self._resolve_and_authorize(
            user=user, organization_id=organization_id, required_permission=required
        )
        decision = await self._gateway.check_report_access(organization_id, report_id)
        await self._audit.append(
            actor_user_id=user.id,
            organization_id=organization_id,
            event_type="organization.reports.access_check",
            operation="read",
            outcome="success",
            resource_type="report",
            resource_id=report_id,
            details={
                "permission": required,
                "tool": "check_organization_report_access",
                "has_access": decision.has_access,
            },
        )
        return decision, access

    async def list_audit_events(
        self, *, user: User, organization_id: str
    ) -> tuple[list[AuditEvent], AccessContext]:
        """Return append-only audit events scoped to a sandbox organization.

        Requires ``audit.read``. Reading the audit log is itself not audited, to
        avoid unbounded self-referential growth.
        """

        required = Permission.AUDIT_READ.value
        _, access = await self._resolve_and_authorize(
            user=user, organization_id=organization_id, required_permission=required
        )
        events = await self._audit.list_for_organization(organization_id)
        return events, access
