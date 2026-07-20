"""User facade combining Test_user1 identity with local access sidecars."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.user.contract import UserDirectory
from app.adapters.user.provider import get_user_directory
from app.db.orm_models import OrganizationMembershipORM, RolePermissionORM
from app.domain.enums import MembershipStatus
from app.domain.models import User


class UserRepository:
    def __init__(
        self,
        session: AsyncSession,
        user_directory: UserDirectory | None = None,
    ) -> None:
        self._session = session
        self._users = user_directory or get_user_directory()

    async def get_by_id(self, user_id: str) -> User | None:
        return await self._users.get_by_id(user_id)

    async def get_by_email(self, email: str) -> User | None:
        return await self._users.get_by_email(email)

    async def get_active_roles(self, user_id: str, organization_id: str) -> list[str]:
        """Return roles from the user's active local organization membership."""

        stmt = select(OrganizationMembershipORM.role).where(
            OrganizationMembershipORM.user_id == str(user_id),
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
    ) -> list[tuple[User, OrganizationMembershipORM]]:
        """Hydrate organization memberships from the sole user directory."""

        statement = (
            select(OrganizationMembershipORM)
            .where(OrganizationMembershipORM.organization_id == organization_id)
            .order_by(OrganizationMembershipORM.id.asc())
        )
        memberships = tuple(
            (await self._session.execute(statement)).scalars().all()
        )
        users = await self._users.get_many_by_ids(
            tuple(item.user_id for item in memberships)
        )
        # This mirrors the old inner join: stale references are not exposed.
        return [
            (users[item.user_id], item)
            for item in memberships
            if item.user_id in users
        ]
