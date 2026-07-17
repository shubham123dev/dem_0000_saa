from __future__ import annotations

from app.adapters.organization.contract import OrganizationApiGateway
from app.core.errors import OrganizationSuspendedError, ProductionAccessBlockedError
from app.domain.enums import Environment, OrganizationStatus, Permission
from app.domain.models import User
from app.permissions.permission_service import PermissionService


class AgentAuthorizationPreflightService:
    def __init__(
        self,
        *,
        organization_gateway: OrganizationApiGateway,
        permission_service: PermissionService,
    ) -> None:
        self._organization_gateway = organization_gateway
        self._permission_service = permission_service

    async def authorize(
        self,
        *,
        user: User,
        organization_id: str,
    ) -> None:
        organization_profile = await self._organization_gateway.get_profile(
            organization_id
        )
        if organization_profile.environment != Environment.SANDBOX:
            raise ProductionAccessBlockedError()
        if organization_profile.status != OrganizationStatus.ACTIVE:
            raise OrganizationSuspendedError()
        await self._permission_service.authorize(
            user=user,
            organization_id=organization_id,
            required_permission=Permission.ORGANIZATION_PROFILE_READ.value,
        )
