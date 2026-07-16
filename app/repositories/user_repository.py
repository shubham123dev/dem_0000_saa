"""User repository: resolves users, memberships, roles, and role permissions.

All authorization inputs (roles, permissions) are read from the database. They
are never accepted from request bodies or user text. Only *active* memberships
grant roles; invited/suspended/removed memberships confer no access.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.orm_models import (
    OrganizationMembershipORM,
    RolePermissionORM,
    UserORM,
)
from app.domain.enums import MembershipStatus, UserStatus
from app.domain.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: str) -> User | None:
        row = await self._session.get(UserORM, user_id)
        if row is None:
            return None
        return User(
            id=row.id,
            display_name=row.display_name,
            email=row.email,
            status=UserStatus(row.status),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def get_active_roles(self, user_id: str, organization_id: str) -> list[str]:
        """Return roles from the user's *active* membership in the org."""

        stmt = select(OrganizationMembershipORM.role).where(
            OrganizationMembershipORM.user_id == user_id,
            OrganizationMembershipORM.organization_id == organization_id,
            OrganizationMembershipORM.membership_status
            == MembershipStatus.ACTIVE.value,
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_permissions_for_roles(self, roles: list[str]) -> set[str]:
        if not roles:
            return set()
        stmt = select(RolePermissionORM.permission).where(
            RolePermissionORM.role.in_(roles)
        )
        result = await self._session.execute(stmt)
        return set(result.scalars().all())

    async def list_memberships(
        self, organization_id: str
    ) -> list[tuple[UserORM, OrganizationMembershipORM]]:
        """Return every (user, membership) pair for an organization."""

        stmt = (
            select(UserORM, OrganizationMembershipORM)
            .join(
                OrganizationMembershipORM,
                OrganizationMembershipORM.user_id == UserORM.id,
            )
            .where(OrganizationMembershipORM.organization_id == organization_id)
            .order_by(OrganizationMembershipORM.id.asc())
        )
        result = await self._session.execute(stmt)
        return [(user, membership) for user, membership in result.all()]
