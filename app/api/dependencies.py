"""FastAPI request dependencies and service wiring.

A dedicated dependencies module keeps construction of repositories, adapters,
and services in one place. This is a concrete technical reason to add a file
beyond the suggested tree.

Two surfaces share the same in-process ``MockOrganizationApi`` backend:

* the raw ``/mock-api/v1`` routes (external system of record stand-in), and
* the enforced ``/workplace`` tools, which reach it through
  ``MockOrganizationApiAdapter`` (the swappable gateway seam).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.organization.mock_adapter import MockOrganizationApiAdapter
from app.core.errors import UnauthenticatedError, UserDisabledError
from app.db.session import get_session
from app.domain.models import User
from app.mock_api.service import MockOrganizationApi
from app.permissions.permission_service import PermissionService
from app.repositories.audit_repository import AuditRepository
from app.repositories.user_repository import UserRepository
from app.services.organization_service import OrganizationService

SessionDep = Annotated[AsyncSession, Depends(get_session)]

# Mock authentication identity source. Only the user *identity* comes from this
# header; roles and permissions are always resolved from the database.
MOCK_USER_HEADER = "X-Mock-User-Id"


def get_user_repository(session: SessionDep) -> UserRepository:
    return UserRepository(session)


def get_audit_repository(session: SessionDep) -> AuditRepository:
    return AuditRepository(session)


def get_mock_organization_api(session: SessionDep) -> MockOrganizationApi:
    """The in-process mock organization backend (shared by both surfaces)."""

    return MockOrganizationApi(session)


MockOrganizationApiDep = Annotated[
    MockOrganizationApi, Depends(get_mock_organization_api)
]


def get_organization_service(
    api: MockOrganizationApiDep,
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
    audit_repo: Annotated[AuditRepository, Depends(get_audit_repository)],
) -> OrganizationService:
    return OrganizationService(
        organization_gateway=MockOrganizationApiAdapter(api),
        permission_service=PermissionService(user_repo),
        audit_repository=audit_repo,
    )


async def get_authenticated_user(
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
    x_mock_user_id: Annotated[str | None, Header(alias=MOCK_USER_HEADER)] = None,
) -> User:
    """Resolve the mock-authenticated user from the request header.

    - Missing header -> 401 unauthenticated
    - Unknown user   -> 401 unauthenticated
    - Disabled user  -> 403 user_disabled

    Roles/permissions are never taken from the header or body; only the user
    identity is. There is no default admin when the header is absent.
    """

    if not x_mock_user_id:
        raise UnauthenticatedError("Missing X-Mock-User-Id header")

    user = await user_repo.get_by_id(x_mock_user_id)
    if user is None:
        raise UnauthenticatedError("Unknown user")

    if not user.is_active:
        raise UserDisabledError()

    return user


UserDep = Annotated[User, Depends(get_authenticated_user)]
OrganizationServiceDep = Annotated[
    OrganizationService, Depends(get_organization_service)
]
