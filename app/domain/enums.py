"""Domain enumerations and canonical permission/role constants.

These are the backend-owned vocabulary. Roles and permissions are never
accepted from the request body or user text.
"""

from __future__ import annotations

from enum import Enum


class Environment(str, Enum):
    """Deployment environment. Step 0 supports only ``sandbox``."""

    SANDBOX = "sandbox"
    # ``production`` is defined only so the backend can explicitly *block* it.
    PRODUCTION = "production"


class OrganizationStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class EmployeeStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


class Role(str, Enum):
    SANDBOX_ADMIN = "sandbox_admin"
    SANDBOX_READER = "sandbox_reader"


class Permission(str, Enum):
    ORGANIZATION_PROFILE_READ = "organization.profile.read"
    # Defined for future steps; Step 0 must not expose or execute an update.
    ORGANIZATION_PROFILE_UPDATE = "organization.profile.update"


# Canonical role -> permission mapping used to seed the ``role_permissions``
# table. The permission service reads authoritative data from the database;
# this constant is the single source of truth for seeding.
ROLE_PERMISSIONS: dict[Role, tuple[Permission, ...]] = {
    Role.SANDBOX_ADMIN: (
        Permission.ORGANIZATION_PROFILE_READ,
        Permission.ORGANIZATION_PROFILE_UPDATE,
    ),
    Role.SANDBOX_READER: (Permission.ORGANIZATION_PROFILE_READ,),
}
