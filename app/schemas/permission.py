"""Permission / access-context schemas."""

from __future__ import annotations

from pydantic import BaseModel


class AccessContext(BaseModel):
    """Resolved backend-owned access context for an authenticated request.

    Roles and permissions here are always derived from the database, never from
    request input or user text.
    """

    user_id: str
    organization_id: str
    roles: list[str]
    permissions: list[str]

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions
