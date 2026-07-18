"""FastAPI request dependencies and service wiring."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.nucleus.contract import NucleusOrganizationGateway
from app.adapters.organization.contract import OrganizationApiGateway
from app.adapters.organization.mock_adapter import MockOrganizationApiAdapter
from app.agent.action_contracts import VersionedOrganizationMutationGateway
from app.core.errors import UnauthenticatedError, UserDisabledError
from app.db.session import get_session
from app.domain.models import User
from app.mock_api.service import MockOrganizationApi
from app.permissions.permission_service import PermissionService
from app.repositories.audit_repository import AuditRepository
from app.repositories.nucleus_organization_repository import NucleusOrganizationRepository
from app.repositories.user_repository import UserRepository
from app.services.nucleus_organization_service import NucleusOrganizationService
from app.services.organization_service import OrganizationService

SessionDep = Annotated[AsyncSession, Depends(get_session)]
MOCK_USER_HEADER = "X-Mock-User-Id"


def get_user_repository(session: SessionDep) -> UserRepository:
    return UserRepository(session)


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
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
    x_mock_user_id: Annotated[str | None, Header(alias=MOCK_USER_HEADER)] = None,
) -> User:
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
NucleusOrganizationServiceDep = Annotated[
    NucleusOrganizationService,
    Depends(get_nucleus_organization_service),
]
