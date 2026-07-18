from __future__ import annotations

from fastapi import APIRouter

from app.api.dependencies import SessionDep, UserDep
from app.domain.enums import Permission
from app.permissions.permission_service import PermissionService
from app.repositories.user_repository import UserRepository
from app.schemas.workplace_resources import (
    WorkplaceResourceCountResponse,
    WorkplaceResourceResponse,
    WorkplaceResourceSchemaResponse,
    WorkplaceResourceSearchRequest,
    WorkplaceResourceSearchResponse,
    WorkplaceResourceTypeListResponse,
)
from app.workplace_resources.errors import (
    WorkplaceResourceInvalidError,
    WorkplaceResourceNotFoundError,
)
from app.workplace_resources.registry import WorkplaceResourceRegistry
from app.workplace_resources.service import WorkplaceResourceService

router = APIRouter(
    prefix="/workplace/organizations/{organization_id}/resources",
    tags=["workplace-resources"],
)


async def _authorize(
    *,
    session: SessionDep,
    user: UserDep,
    organization_id: str,
) -> None:
    await PermissionService(UserRepository(session)).authorize(
        user=user,
        organization_id=organization_id,
        required_permission=Permission.WORKPLACE_RESOURCES_READ.value,
    )


@router.get("", response_model=WorkplaceResourceTypeListResponse)
async def list_resource_types(
    organization_id: str,
    session: SessionDep,
    user: UserDep,
) -> WorkplaceResourceTypeListResponse:
    await _authorize(
        session=session,
        user=user,
        organization_id=organization_id,
    )
    service = WorkplaceResourceService(session, WorkplaceResourceRegistry())
    return WorkplaceResourceTypeListResponse(
        resources=service.list_resource_types()
    )


@router.get(
    "/{resource_type}/schema",
    response_model=WorkplaceResourceSchemaResponse,
)
async def describe_resource(
    organization_id: str,
    resource_type: str,
    session: SessionDep,
    user: UserDep,
) -> WorkplaceResourceSchemaResponse:
    await _authorize(
        session=session,
        user=user,
        organization_id=organization_id,
    )
    service = WorkplaceResourceService(session, WorkplaceResourceRegistry())
    try:
        resource = service.describe(resource_type)
    except ValueError as exception:
        raise WorkplaceResourceInvalidError(str(exception)) from exception
    return WorkplaceResourceSchemaResponse(resource=resource)


@router.post(
    "/{resource_type}/search",
    response_model=WorkplaceResourceSearchResponse,
)
async def search_resources(
    organization_id: str,
    resource_type: str,
    request: WorkplaceResourceSearchRequest,
    session: SessionDep,
    user: UserDep,
) -> WorkplaceResourceSearchResponse:
    await _authorize(
        session=session,
        user=user,
        organization_id=organization_id,
    )
    service = WorkplaceResourceService(session, WorkplaceResourceRegistry())
    try:
        items, total = await service.search(
            organization_id=organization_id,
            resource_type=resource_type,
            filters=request.filters,
            sort_by=request.sort_by,
            descending=request.descending,
            limit=request.limit,
            offset=request.offset,
        )
    except ValueError as exception:
        raise WorkplaceResourceInvalidError(str(exception)) from exception
    return WorkplaceResourceSearchResponse(
        items=items,
        total=total,
        limit=request.limit,
        offset=request.offset,
    )


@router.post(
    "/{resource_type}/count",
    response_model=WorkplaceResourceCountResponse,
)
async def count_resources(
    organization_id: str,
    resource_type: str,
    request: WorkplaceResourceSearchRequest,
    session: SessionDep,
    user: UserDep,
) -> WorkplaceResourceCountResponse:
    await _authorize(
        session=session,
        user=user,
        organization_id=organization_id,
    )
    service = WorkplaceResourceService(session, WorkplaceResourceRegistry())
    try:
        _, total = await service.search(
            organization_id=organization_id,
            resource_type=resource_type,
            filters=request.filters,
            sort_by=None,
            descending=False,
            limit=1,
            offset=0,
        )
    except ValueError as exception:
        raise WorkplaceResourceInvalidError(str(exception)) from exception
    return WorkplaceResourceCountResponse(count=total)


@router.get(
    "/{resource_type}/{resource_id}",
    response_model=WorkplaceResourceResponse,
)
async def get_resource(
    organization_id: str,
    resource_type: str,
    resource_id: str,
    session: SessionDep,
    user: UserDep,
) -> WorkplaceResourceResponse:
    await _authorize(
        session=session,
        user=user,
        organization_id=organization_id,
    )
    service = WorkplaceResourceService(session, WorkplaceResourceRegistry())
    try:
        item = await service.get(
            organization_id=organization_id,
            resource_type=resource_type,
            resource_id=resource_id,
        )
    except ValueError as exception:
        raise WorkplaceResourceInvalidError(str(exception)) from exception
    if item is None:
        raise WorkplaceResourceNotFoundError()
    return WorkplaceResourceResponse(item=item)
