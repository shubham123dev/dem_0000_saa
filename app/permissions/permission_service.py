"""Permission service.

Enforces backend-owned authorization: organization membership and required
permissions are resolved from the database. Authorization is never derived from
request bodies or user-provided text.
"""

from __future__ import annotations

from app.core.errors import (
    OrganizationAccessDeniedError,
    PermissionDeniedError,
)
from app.domain.models import Employee
from app.repositories.employee_repository import EmployeeRepository
from app.schemas.permission import AccessContext


class PermissionService:
    def __init__(self, employee_repository: EmployeeRepository) -> None:
        self._employees = employee_repository

    async def authorize(
        self,
        *,
        employee: Employee,
        organization_id: str,
        required_permission: str,
    ) -> AccessContext:
        """Resolve and enforce access for a permission within an organization.

        Raises:
            OrganizationAccessDeniedError: employee has no role in the org.
            PermissionDeniedError: employee lacks the required permission.
        """

        roles = await self._employees.get_roles(employee.id, organization_id)
        if not roles:
            raise OrganizationAccessDeniedError()

        permissions = await self._employees.get_permissions_for_roles(roles)
        if required_permission not in permissions:
            raise PermissionDeniedError(
                f"Employee does not have {required_permission} permission"
            )

        return AccessContext(
            employee_id=employee.id,
            organization_id=organization_id,
            roles=sorted(roles),
            permissions=sorted(permissions),
        )
