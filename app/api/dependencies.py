"""FastAPI request dependencies and service wiring.

A dedicated dependencies module keeps construction of repositories, adapters,
and services in one place. This is a concrete technical reason to add a file
beyond the suggested tree.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.organization.mock_adapter import MockOrganizationAdapter
from app.core.errors import EmployeeDisabledError, UnauthenticatedError
from app.db.session import get_session
from app.domain.models import Employee
from app.permissions.permission_service import PermissionService
from app.repositories.audit_repository import AuditRepository
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.organization_repository import OrganizationRepository
from app.services.organization_service import OrganizationService

SessionDep = Annotated[AsyncSession, Depends(get_session)]

MOCK_EMPLOYEE_HEADER = "X-Mock-Employee-Id"


def get_employee_repository(session: SessionDep) -> EmployeeRepository:
    return EmployeeRepository(session)


def get_organization_repository(session: SessionDep) -> OrganizationRepository:
    return OrganizationRepository(session)


def get_audit_repository(session: SessionDep) -> AuditRepository:
    return AuditRepository(session)


def get_organization_service(
    org_repo: Annotated[OrganizationRepository, Depends(get_organization_repository)],
    employee_repo: Annotated[EmployeeRepository, Depends(get_employee_repository)],
    audit_repo: Annotated[AuditRepository, Depends(get_audit_repository)],
) -> OrganizationService:
    return OrganizationService(
        organization_gateway=MockOrganizationAdapter(org_repo),
        permission_service=PermissionService(employee_repo),
        audit_repository=audit_repo,
    )


async def get_authenticated_employee(
    employee_repo: Annotated[EmployeeRepository, Depends(get_employee_repository)],
    x_mock_employee_id: Annotated[str | None, Header(alias=MOCK_EMPLOYEE_HEADER)] = None,
) -> Employee:
    """Resolve the mock-authenticated employee from the request header.

    - Missing header -> 401 unauthenticated
    - Unknown employee -> 401 unauthenticated
    - Disabled employee -> 403 employee_disabled

    Roles/permissions are never taken from the header or body; only the
    employee identity is. There is no default admin when the header is absent.
    """

    if not x_mock_employee_id:
        raise UnauthenticatedError("Missing X-Mock-Employee-Id header")

    employee = await employee_repo.get_by_id(x_mock_employee_id)
    if employee is None:
        raise UnauthenticatedError("Unknown employee")

    if not employee.is_active:
        raise EmployeeDisabledError()

    return employee


EmployeeDep = Annotated[Employee, Depends(get_authenticated_employee)]
OrganizationServiceDep = Annotated[
    OrganizationService, Depends(get_organization_service)
]
