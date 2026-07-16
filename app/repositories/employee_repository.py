"""Employee repository: resolves employees, roles, and role permissions.

All authorization inputs (roles, permissions) are read from the database. They
are never accepted from request bodies or user text.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.orm_models import (
    EmployeeORM,
    EmployeeOrganizationRoleORM,
    RolePermissionORM,
)
from app.domain.enums import EmployeeStatus
from app.domain.models import Employee


class EmployeeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, employee_id: str) -> Employee | None:
        row = await self._session.get(EmployeeORM, employee_id)
        if row is None:
            return None
        return Employee(
            id=row.id,
            display_name=row.display_name,
            email=row.email,
            status=EmployeeStatus(row.status),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def get_roles(self, employee_id: str, organization_id: str) -> list[str]:
        stmt = select(EmployeeOrganizationRoleORM.role).where(
            EmployeeOrganizationRoleORM.employee_id == employee_id,
            EmployeeOrganizationRoleORM.organization_id == organization_id,
        )
        result = await self._session.execute(stmt)
        return [r for r in result.scalars().all()]

    async def get_permissions_for_roles(self, roles: list[str]) -> set[str]:
        if not roles:
            return set()
        stmt = select(RolePermissionORM.permission).where(
            RolePermissionORM.role.in_(roles)
        )
        result = await self._session.execute(stmt)
        return set(result.scalars().all())
