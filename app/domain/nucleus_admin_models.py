"""Framework-neutral state used by Nucleus administrative actions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True)
class NucleusAccountAdminState:
    organization_account_id: int
    login_username: str
    max_user_limit: int
    license_start_date: datetime | None
    license_end_date: datetime | None
    status: str
    approved_by: int | None
    approved_date: datetime | None
    rejected_by: int | None
    rejected_date: datetime | None
    rejection_reason: str | None
    is_active: bool
    version: int


@dataclass(frozen=True)
class NucleusManagedAccess:
    resource_type: str
    access_id: int
    organization_account_id: int
    values: dict[str, int | None]
    revoked: bool
    version: int


@dataclass(frozen=True)
class NucleusLicenseProjectionState:
    seat_pool_id: str
    total_seats: int
    starts_at: datetime | None
    expires_at: datetime | None
    seat_pool_status: str
    seat_pool_version: int
    active_assignments: int
    renewal_date: date | None
    overview_version: int


@dataclass(frozen=True)
class NucleusLifecycleProjectionState:
    organization_status: str
    organization_version: int
    seat_pool_id: str
    seat_pool_status: str
    seat_pool_version: int


def managed_access_snapshot(access: NucleusManagedAccess) -> dict[str, Any]:
    return {
        "resource_type": access.resource_type,
        "access_id": access.access_id,
        **access.values,
        "revoked": access.revoked,
        "version": access.version,
    }
