"""Permission service.

Enforces backend-owned authorization: organization membership and required
permissions are resolved from the database. Authorization is never derived from
request bodies or user-provided text.

Only *active* memberships grant roles. Invited, suspended, or removed
memberships confer no access, so those users are denied at the organization
boundary.
"""

from __future__ import annotations

from app.core.errors import (
    OrganizationAccessDeniedError,
    PermissionDeniedError,
)
from app.domain.models import User
from app.repositories.user_repository import UserRepository
from app.schemas.permission import AccessContext


class PermissionService:
    def __init__(self, user_repository: UserRepository) -> None:
        self._users = user_repository

    async def authorize(
        self,
        *,
        user: User,
        organization_id: str,
        required_permission: str,
    ) -> AccessContext:
        """Resolve and enforce access for a permission within an organization.

        The pipeline (backend data decides, never the caller):
            active user (checked at authentication)
            → active membership in the organization
            → membership role grants the required permission

        Raises:
            OrganizationAccessDeniedError: user has no active membership.
            PermissionDeniedError: user lacks the required permission.
        """

        roles = await self._users.get_active_roles(user.id, organization_id)
        if not roles:
            raise OrganizationAccessDeniedError()

        permissions = await self._users.get_permissions_for_roles(roles)
        if required_permission not in permissions:
            raise PermissionDeniedError(
                f"User does not have {required_permission} permission"
            )

        return AccessContext(
            user_id=user.id,
            organization_id=organization_id,
            roles=sorted(roles),
            permissions=sorted(permissions),
        )
