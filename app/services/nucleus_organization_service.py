"""Permission-enforced reads for the exact-schema Nucleus SQLite mock."""

from __future__ import annotations

from app.adapters.organization.contract import OrganizationApiGateway
from app.core.errors import (
    OrganizationNotFoundError,
    OrganizationSuspendedError,
    ProductionAccessBlockedError,
)
from app.domain.enums import Environment, OrganizationStatus, Permission
from app.domain.models import User
from app.domain.nucleus_models import (
    NucleusOrganizationAccount,
    NucleusOrganizationApprovalStatus,
    NucleusOrganizationEntitlements,
    NucleusOrganizationLicense,
)
from app.permissions.permission_service import PermissionService
from app.repositories.audit_repository import AuditRepository
from app.repositories.nucleus_organization_repository import NucleusOrganizationRepository
from app.schemas.permission import AccessContext


class NucleusOrganizationService:
    def __init__(
        self,
        *,
        organization_gateway: OrganizationApiGateway,
        permission_service: PermissionService,
        repository: NucleusOrganizationRepository,
        audit_repository: AuditRepository,
    ) -> None:
        self._organization_gateway = organization_gateway
        self._permission_service = permission_service
        self._repository = repository
        self._audit_repository = audit_repository

    async def _authorize(
        self,
        *,
        user: User,
        organization_id: str,
        required_permission: str,
    ) -> AccessContext:
        profile = await self._organization_gateway.get_profile(organization_id)
        if profile.environment != Environment.SANDBOX:
            raise ProductionAccessBlockedError()
        if profile.status != OrganizationStatus.ACTIVE:
            raise OrganizationSuspendedError()
        return await self._permission_service.authorize(
            user=user,
            organization_id=organization_id,
            required_permission=required_permission,
        )

    async def read_account(
        self,
        *,
        user: User,
        organization_id: str,
    ) -> tuple[NucleusOrganizationAccount, AccessContext]:
        permission = Permission.ORGANIZATION_ACCOUNT_READ.value
        access = await self._authorize(
            user=user,
            organization_id=organization_id,
            required_permission=permission,
        )
        account = await self._repository.get_account(organization_id)
        if account is None:
            raise OrganizationNotFoundError()
        await self._audit_repository.append(
            actor_user_id=user.id,
            organization_id=organization_id,
            event_type="nucleus.organization_account.read",
            operation="read",
            outcome="success",
            resource_type="OrganizationAccount",
            resource_id=str(account.organization_account_id),
            details={
                "permission": permission,
                "tool": "get_nucleus_organization_account",
            },
        )
        return account, access

    async def read_license(
        self,
        *,
        user: User,
        organization_id: str,
    ) -> tuple[NucleusOrganizationLicense, AccessContext]:
        permission = Permission.ORGANIZATION_ACCOUNT_READ.value
        access = await self._authorize(
            user=user,
            organization_id=organization_id,
            required_permission=permission,
        )
        license_info = await self._repository.get_license(organization_id)
        if license_info is None:
            raise OrganizationNotFoundError()
        await self._audit_repository.append(
            actor_user_id=user.id,
            organization_id=organization_id,
            event_type="nucleus.organization_license.read",
            operation="read",
            outcome="success",
            resource_type="OrganizationAccount",
            resource_id=str(license_info.organization_account_id),
            details={
                "permission": permission,
                "tool": "get_nucleus_organization_license",
            },
        )
        return license_info, access

    async def read_approval_status(
        self,
        *,
        user: User,
        organization_id: str,
    ) -> tuple[NucleusOrganizationApprovalStatus, AccessContext]:
        permission = Permission.ORGANIZATION_ACCOUNT_READ.value
        access = await self._authorize(
            user=user,
            organization_id=organization_id,
            required_permission=permission,
        )
        approval = await self._repository.get_approval_status(organization_id)
        if approval is None:
            raise OrganizationNotFoundError()
        await self._audit_repository.append(
            actor_user_id=user.id,
            organization_id=organization_id,
            event_type="nucleus.organization_approval.read",
            operation="read",
            outcome="success",
            resource_type="OrganizationAccount",
            resource_id=str(approval.organization_account_id),
            details={
                "permission": permission,
                "tool": "get_nucleus_organization_approval_status",
            },
        )
        return approval, access

    async def read_entitlements(
        self,
        *,
        user: User,
        organization_id: str,
    ) -> tuple[NucleusOrganizationEntitlements, AccessContext]:
        permission = Permission.ORGANIZATION_ENTITLEMENTS_READ.value
        access = await self._authorize(
            user=user,
            organization_id=organization_id,
            required_permission=permission,
        )
        entitlements = await self._repository.get_entitlements(organization_id)
        if entitlements is None:
            raise OrganizationNotFoundError()
        await self._audit_repository.append(
            actor_user_id=user.id,
            organization_id=organization_id,
            event_type="nucleus.organization_entitlements.read",
            operation="read",
            outcome="success",
            resource_type="organization_entitlements",
            resource_id=str(entitlements.organization_account_id),
            details={
                "permission": permission,
                "tool": "get_nucleus_organization_entitlements",
                "category_count": len(entitlements.category_access),
                "company_profile_count": len(entitlements.company_profile_access),
                "drug_count": len(entitlements.drug_access),
                "indication_count": len(entitlements.indication_access),
                "market_count": len(entitlements.market_access),
                "report_count": len(entitlements.report_access),
                "special_permission_rows": len(entitlements.special_permissions),
            },
        )
        return entitlements, access
