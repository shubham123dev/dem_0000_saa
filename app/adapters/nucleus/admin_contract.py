"""Ports for privileged Nucleus administration and legacy projections."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from app.domain.nucleus_admin_models import (
    NucleusAccountAdminState,
    NucleusLicenseProjectionState,
    NucleusLifecycleProjectionState,
    NucleusManagedAccess,
)


@runtime_checkable
class NucleusAdministrationGateway(Protocol):
    async def get_admin_state(
        self, organization_code: str
    ) -> NucleusAccountAdminState | None:
        ...

    async def get_username_owner_id(self, username: str) -> int | None:
        ...

    async def update_username_if_version(
        self,
        *,
        organization_code: str,
        username: str,
        actor_id: int,
        expected_version: int,
    ) -> NucleusAccountAdminState | None:
        ...

    async def update_license_if_version(
        self,
        *,
        organization_code: str,
        max_user_limit: int,
        license_start_date: datetime | None,
        license_end_date: datetime | None,
        actor_id: int,
        expected_version: int,
    ) -> NucleusAccountAdminState | None:
        ...

    async def transition_approval_if_version(
        self,
        *,
        organization_code: str,
        decision: str,
        reason: str | None,
        actor_id: int,
        expected_version: int,
    ) -> NucleusAccountAdminState | None:
        ...

    async def set_active_if_version(
        self,
        *,
        organization_code: str,
        is_active: bool,
        actor_id: int,
        expected_version: int,
    ) -> NucleusAccountAdminState | None:
        ...

    async def inspect_access(
        self,
        *,
        organization_code: str,
        access_kind: str,
        values: dict[str, int | None],
    ) -> tuple[NucleusManagedAccess | None, int] | None:
        ...

    async def get_access(
        self,
        *,
        organization_code: str,
        access_kind: str,
        access_id: int,
    ) -> NucleusManagedAccess | None:
        ...

    async def grant_access_if_version(
        self,
        *,
        organization_code: str,
        access_kind: str,
        values: dict[str, int | None],
        actor_id: int,
        expected_version: int,
    ) -> NucleusManagedAccess | None:
        ...

    async def revoke_access_if_version(
        self,
        *,
        organization_code: str,
        access_kind: str,
        access_id: int,
        actor_id: int,
        expected_version: int,
    ) -> NucleusManagedAccess | None:
        ...


@runtime_checkable
class NucleusAdministrationProjectionGateway(Protocol):
    async def get_license_projection(
        self, organization_id: str
    ) -> NucleusLicenseProjectionState | None:
        ...

    async def update_license_projection_if_versions(
        self,
        *,
        organization_id: str,
        max_user_limit: int,
        license_start_date: datetime | None,
        license_end_date: datetime | None,
        expected_seat_pool_version: int,
        expected_overview_version: int,
    ) -> NucleusLicenseProjectionState | None:
        ...

    async def get_lifecycle_projection(
        self, organization_id: str
    ) -> NucleusLifecycleProjectionState | None:
        ...

    async def update_lifecycle_projection_if_versions(
        self,
        *,
        organization_id: str,
        should_be_active: bool,
        license_end_date: datetime | None,
        expected_organization_version: int,
        expected_seat_pool_version: int,
    ) -> NucleusLifecycleProjectionState | None:
        ...
