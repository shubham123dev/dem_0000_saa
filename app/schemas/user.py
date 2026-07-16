"""User and organization-membership API schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.domain.enums import MembershipStatus, UserStatus
from app.domain.models import OrganizationMember
from app.schemas.organization import OrganizationAccessOut


class UserOut(BaseModel):
    """Public user representation (never exposes ORM objects)."""

    id: str
    display_name: str
    email: str
    status: UserStatus


class OrganizationMemberOut(BaseModel):
    """A member of an organization plus derived seat status.

    ``has_active_seat`` shows that users and seats are distinct: an active
    member may not occupy a licensed seat.
    """

    user_id: str
    display_name: str
    email: str
    user_status: UserStatus
    role: str
    membership_status: MembershipStatus
    has_active_seat: bool
    joined_at: datetime | None = None

    @classmethod
    def from_domain(cls, member: OrganizationMember) -> "OrganizationMemberOut":
        return cls(
            user_id=member.user_id,
            display_name=member.display_name,
            email=member.email,
            user_status=member.user_status,
            role=member.role,
            membership_status=member.membership_status,
            has_active_seat=member.has_active_seat,
            joined_at=member.joined_at,
        )


class OrganizationUsersResponse(BaseModel):
    """Response body for the list-organization-users endpoint."""

    organization_id: str
    members: list[OrganizationMemberOut]
    access: OrganizationAccessOut
