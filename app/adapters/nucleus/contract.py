"""Port consumed by Nucleus organization services and action handlers.

Implementations may use the exact-schema SQLite sandbox, a future Nucleus
HTTP API, or another production-safe persistence adapter. Callers depend
only on this framework-neutral contract.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from app.domain.nucleus_models import (
    NucleusCategoryAccess,
    NucleusOrganizationAccount,
    NucleusOrganizationApprovalStatus,
    NucleusOrganizationEntitlements,
    NucleusOrganizationLicense,
    NucleusReportAccess,
    NucleusSpecialPermissions,
)


@runtime_checkable
class NucleusOrganizationGateway(Protocol):
    async def get_account(
        self,
        organization_code: str,
    ) -> NucleusOrganizationAccount | None:
        ...

    async def get_license(
        self,
        organization_code: str,
    ) -> NucleusOrganizationLicense | None:
        ...

    async def get_approval_status(
        self,
        organization_code: str,
    ) -> NucleusOrganizationApprovalStatus | None:
        ...

    async def get_entitlements(
        self,
        organization_code: str,
    ) -> NucleusOrganizationEntitlements | None:
        ...

    async def get_account_field_state(
        self,
        organization_code: str,
        field_name: str,
    ) -> tuple[NucleusOrganizationAccount, Any] | None:
        ...

    async def get_contact_email_bridge_state(
        self,
        organization_code: str,
    ) -> tuple[NucleusOrganizationAccount, int] | None:
        ...

    async def update_contact_email_bridge_if_version(
        self,
        *,
        organization_code: str,
        value: str,
        expected_legacy_version: int,
        expected_nucleus_email: str | None,
    ) -> NucleusOrganizationAccount | None:
        ...

    async def update_account_field_if_version(
        self,
        *,
        organization_code: str,
        field_name: str,
        value: str | None,
        expected_version: int,
    ) -> NucleusOrganizationAccount | None:
        ...

    async def inspect_category_grant(
        self,
        *,
        organization_code: str,
        category_id: int,
        category_sample_id: int | None,
    ) -> tuple[NucleusCategoryAccess | None, int] | None:
        ...

    async def get_category_access(
        self,
        *,
        organization_code: str,
        access_id: int,
    ) -> NucleusCategoryAccess | None:
        ...

    async def grant_category_access_if_version(
        self,
        *,
        organization_code: str,
        category_id: int,
        category_sample_id: int | None,
        expected_version: int,
    ) -> NucleusCategoryAccess | None:
        ...

    async def revoke_category_access_if_version(
        self,
        *,
        organization_code: str,
        access_id: int,
        expected_version: int,
    ) -> NucleusCategoryAccess | None:
        ...

    async def inspect_report_grant(
        self,
        *,
        organization_code: str,
        reports_id: int | None,
        sample_id: int | None,
        sample_toc_id: int | None,
        speciality_id: int | None,
        is_executive_access: bool | None,
    ) -> tuple[NucleusReportAccess | None, int] | None:
        ...

    async def get_report_access(
        self,
        *,
        organization_code: str,
        access_id: int,
    ) -> NucleusReportAccess | None:
        ...

    async def grant_report_access_if_version(
        self,
        *,
        organization_code: str,
        reports_id: int | None,
        sample_id: int | None,
        sample_toc_id: int | None,
        speciality_id: int | None,
        is_executive_access: bool | None,
        expected_version: int,
    ) -> NucleusReportAccess | None:
        ...

    async def revoke_report_access_if_version(
        self,
        *,
        organization_code: str,
        access_id: int,
        expected_version: int,
    ) -> NucleusReportAccess | None:
        ...

    async def get_permission(
        self,
        *,
        organization_code: str,
        permission_id: int,
    ) -> NucleusSpecialPermissions | None:
        ...

    async def set_permission_if_version(
        self,
        *,
        organization_code: str,
        permission_id: int | None,
        values: dict[str, int | bool | None],
        expected_version: int,
    ) -> NucleusSpecialPermissions | None:
        ...
