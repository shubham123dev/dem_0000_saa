"""Domain enumerations and canonical permission/role constants.

These are the backend-owned vocabulary. Roles and permissions are never
accepted from request bodies or user text.
"""

from __future__ import annotations

from enum import Enum


class Environment(str, Enum):
    """Deployment environment. The current product supports sandbox only."""

    SANDBOX = "sandbox"
    # Defined only so the backend can explicitly block production access.
    PRODUCTION = "production"


class OrganizationStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class UserStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


class Role(str, Enum):
    SANDBOX_ADMIN = "sandbox_admin"
    SANDBOX_READER = "sandbox_reader"


class MembershipStatus(str, Enum):
    INVITED = "invited"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REMOVED = "removed"


class SeatType(str, Enum):
    STANDARD = "standard"


class SeatPoolStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"


class SeatAssignmentStatus(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class ReportStatus(str, Enum):
    ACTIVE = "active"
    RETIRED = "retired"


class ReportAccessLevel(str, Enum):
    VIEW = "view"
    CHAT = "chat"
    DOWNLOAD = "download"
    FULL = "full"


class ReportAccessStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"
    REVOKED = "revoked"


class Permission(str, Enum):
    ORGANIZATION_PROFILE_READ = "organization.profile.read"
    ORGANIZATION_PROFILE_UPDATE = "organization.profile.update"

    ORGANIZATION_USERS_READ = "organization.users.read"
    ORGANIZATION_USERS_INVITE = "organization.users.invite"
    ORGANIZATION_USERS_UPDATE = "organization.users.update"
    ORGANIZATION_USERS_REMOVE = "organization.users.remove"

    ORGANIZATION_SEATS_READ = "organization.seats.read"
    ORGANIZATION_SEATS_ASSIGN = "organization.seats.assign"
    ORGANIZATION_SEATS_REVOKE = "organization.seats.revoke"

    ORGANIZATION_REPORTS_READ = "organization.reports.read"
    ORGANIZATION_REPORTS_GRANT = "organization.reports.grant"
    ORGANIZATION_REPORTS_REVOKE = "organization.reports.revoke"

    AGENT_ACTIONS_READ = "agent.actions.read"
    AGENT_ACTIONS_APPROVE = "agent.actions.approve"
    AGENT_ACTIONS_EXECUTE = "agent.actions.execute"
    AGENT_ACTIONS_RECONCILE = "agent.actions.reconcile"

    AUDIT_READ = "audit.read"


_READER_PERMISSIONS: tuple[Permission, ...] = (
    Permission.ORGANIZATION_PROFILE_READ,
    Permission.ORGANIZATION_USERS_READ,
    Permission.ORGANIZATION_SEATS_READ,
    Permission.ORGANIZATION_REPORTS_READ,
    Permission.AUDIT_READ,
)

_ADMIN_ONLY_PERMISSIONS: tuple[Permission, ...] = (
    Permission.ORGANIZATION_PROFILE_UPDATE,
    Permission.ORGANIZATION_USERS_INVITE,
    Permission.ORGANIZATION_USERS_UPDATE,
    Permission.ORGANIZATION_USERS_REMOVE,
    Permission.ORGANIZATION_SEATS_ASSIGN,
    Permission.ORGANIZATION_SEATS_REVOKE,
    Permission.ORGANIZATION_REPORTS_GRANT,
    Permission.ORGANIZATION_REPORTS_REVOKE,
    Permission.AGENT_ACTIONS_READ,
    Permission.AGENT_ACTIONS_APPROVE,
    Permission.AGENT_ACTIONS_EXECUTE,
    Permission.AGENT_ACTIONS_RECONCILE,
)


ROLE_PERMISSIONS: dict[Role, tuple[Permission, ...]] = {
    Role.SANDBOX_ADMIN: _READER_PERMISSIONS + _ADMIN_ONLY_PERMISSIONS,
    Role.SANDBOX_READER: _READER_PERMISSIONS,
}
