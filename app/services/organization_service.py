"""Organization service: orchestrates the Step 0 read-only flow.

Flow:
    resolve organization (via adapter contract)
    → enforce sandbox-only environment (block production)
    → authorize employee (membership + permission)
    → append read audit event
    → return exact profile + access context

The service depends on the ``OrganizationGateway`` adapter contract, never on
the ORM directly.
"""

from __future__ import annotations

from app.adapters.organization.contract import OrganizationGateway
from app.core.errors import ProductionAccessBlockedError
from app.domain.enums import Environment, Permission
from app.domain.models import Employee, OrganizationProfile
from app.permissions.permission_service import PermissionService
from app.repositories.audit_repository import AuditRepository
from app.schemas.permission import AccessContext


class OrganizationService:
    def __init__(
        self,
        *,
        organization_gateway: OrganizationGateway,
        permission_service: PermissionService,
        audit_repository: AuditRepository,
    ) -> None:
        self._gateway = organization_gateway
        self._permissions = permission_service
        self._audit = audit_repository

    async def read_profile(
        self, *, employee: Employee, organization_id: str
    ) -> tuple[OrganizationProfile, AccessContext]:
        """Read a sandbox organization profile and record a read audit event."""

        # 1. Resolve the organization (raises OrganizationNotFoundError -> 404).
        profile = await self._gateway.get_profile(organization_id)

        # 2. Sandbox-only enforcement. Production access is explicitly blocked.
        if profile.environment != Environment.SANDBOX:
            raise ProductionAccessBlockedError()

        # 3. Backend-owned authorization (membership + required permission).
        required = Permission.ORGANIZATION_PROFILE_READ.value
        access = await self._permissions.authorize(
            employee=employee,
            organization_id=organization_id,
            required_permission=required,
        )

        # 4. Record the append-only read audit event.
        await self._audit.append(
            actor_employee_id=employee.id,
            organization_id=organization_id,
            event_type="organization.profile.read",
            operation="read",
            outcome="success",
            resource_type="organization",
            resource_id=organization_id,
            details={"permission": required, "tool": "get_organization_profile"},
        )

        return profile, access

    async def list_audit_events(
        self, *, employee: Employee, organization_id: str
    ):
        """Return append-only audit events scoped to a sandbox organization.

        Requires ``organization.profile.read`` in Step 0.
        """

        # Resolve + sandbox enforcement so audit reads honor the same bounds.
        profile = await self._gateway.get_profile(organization_id)
        if profile.environment != Environment.SANDBOX:
            raise ProductionAccessBlockedError()

        await self._permissions.authorize(
            employee=employee,
            organization_id=organization_id,
            required_permission=Permission.ORGANIZATION_PROFILE_READ.value,
        )

        return await self._audit.list_for_organization(organization_id)
