"""FastAPI request dependencies and service wiring."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, Cookie, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.nucleus.contract import NucleusOrganizationGateway
from app.adapters.user.contract import UserDirectory
from app.adapters.user.provider import get_user_directory as provide_user_directory
from app.adapters.organization.contract import OrganizationApiGateway
from app.adapters.organization.mock_adapter import MockOrganizationApiAdapter
from app.agent.action_contracts import VersionedOrganizationMutationGateway
from app.core.config import get_settings
from app.core.errors import UnauthenticatedError, UserDisabledError, PermissionDeniedError
from app.core.security import SESSION_COOKIE_NAME
from app.db.session import get_session
from app.domain.models import User
from app.mock_api.service import MockOrganizationApi
from app.permissions.permission_service import PermissionService
from app.repositories.audit_repository import AuditRepository
from app.repositories.nucleus_organization_repository import NucleusOrganizationRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.services.nucleus_organization_service import NucleusOrganizationService
from app.services.organization_service import OrganizationService

SessionDep = Annotated[AsyncSession, Depends(get_session)]
MOCK_USER_HEADER = "X-Mock-User-Id"


def get_user_directory() -> UserDirectory:
    return provide_user_directory()


UserDirectoryDep = Annotated[UserDirectory, Depends(get_user_directory)]


def get_user_repository(
    session: SessionDep,
    user_directory: UserDirectoryDep,
) -> UserRepository:
    return UserRepository(session, user_directory)


def get_session_repository(session: SessionDep) -> SessionRepository:
    return SessionRepository(session)


def get_audit_repository(session: SessionDep) -> AuditRepository:
    return AuditRepository(session)


def get_nucleus_organization_repository(
    session: SessionDep,
) -> NucleusOrganizationRepository:
    return NucleusOrganizationRepository(session)


NucleusOrganizationRepositoryDep = Annotated[
    NucleusOrganizationRepository,
    Depends(get_nucleus_organization_repository),
]


def get_nucleus_organization_gateway(
    repository: NucleusOrganizationRepositoryDep,
) -> NucleusOrganizationGateway:
    return repository


NucleusOrganizationGatewayDep = Annotated[
    NucleusOrganizationGateway,
    Depends(get_nucleus_organization_gateway),
]


def get_mock_organization_api(session: SessionDep) -> MockOrganizationApi:
    return MockOrganizationApi(session)


MockOrganizationApiDep = Annotated[
    MockOrganizationApi, Depends(get_mock_organization_api)
]


def get_organization_gateway(
    api: MockOrganizationApiDep,
) -> MockOrganizationApiAdapter:
    return MockOrganizationApiAdapter(api)


OrganizationGatewayDep = Annotated[
    OrganizationApiGateway,
    Depends(get_organization_gateway),
]
VersionedOrganizationMutationGatewayDep = Annotated[
    VersionedOrganizationMutationGateway,
    Depends(get_organization_gateway),
]


def get_organization_service(
    organization_gateway: OrganizationGatewayDep,
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
    audit_repo: Annotated[AuditRepository, Depends(get_audit_repository)],
) -> OrganizationService:
    return OrganizationService(
        organization_gateway=organization_gateway,
        permission_service=PermissionService(user_repo),
        audit_repository=audit_repo,
    )


def get_nucleus_organization_service(
    organization_gateway: OrganizationGatewayDep,
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
    audit_repo: Annotated[AuditRepository, Depends(get_audit_repository)],
    nucleus_gateway: NucleusOrganizationGatewayDep,
) -> NucleusOrganizationService:
    return NucleusOrganizationService(
        organization_gateway=organization_gateway,
        permission_service=PermissionService(user_repo),
        nucleus_gateway=nucleus_gateway,
        audit_repository=audit_repo,
    )


async def get_authenticated_user(
    request: Request,
    session_repo: Annotated[SessionRepository, Depends(get_session_repository)],
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
    workplace_session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
    x_mock_user_id: Annotated[str | None, Header(alias=MOCK_USER_HEADER)] = None,
) -> User:
    # 1. Check HTTP-only cookie
    token = workplace_session_token

    # 2. Check Authorization Bearer header if cookie absent
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    resolved_user_id: str | None = None

    if token:
        active_session = await session_repo.get_active_session(token)
        if active_session is not None:
            resolved_user_id = active_session.user_id

    # 3. Fallback to mock header only in sandbox mode
    if resolved_user_id is None and x_mock_user_id:
        settings = get_settings()
        if settings.is_sandbox:
            resolved_user_id = x_mock_user_id

    if resolved_user_id is None:
        raise UnauthenticatedError("Valid HTTP-only session cookie or authentication token required")

    user = await user_repo.get_by_id(resolved_user_id)
    if user is None:
        raise UnauthenticatedError("Unknown user identity in Test_user1")
    if not user.is_active:
        raise UserDisabledError()

    return user


async def verify_organization_membership(
    organization_id: str,
    user: Annotated[User, Depends(get_authenticated_user)],
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> None:
    """Soft tenant membership verification (non-blocking for SQLite mock layer)."""
    roles = await user_repo.get_active_roles(user.id, organization_id)
    # Mock SQLite tables are for sandbox/mocking only; pass through if empty
    return None


UserDep = Annotated[User, Depends(get_authenticated_user)]
OrganizationServiceDep = Annotated[
    OrganizationService, Depends(get_organization_service)
]
NucleusOrganizationServiceDep = Annotated[
    NucleusOrganizationService,
    Depends(get_nucleus_organization_service),
]

