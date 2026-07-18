"""Resolve authenticated Workplace users to Nucleus integer actor IDs."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.nucleus_admin_models import NucleusActorMappingORM


class NucleusActorMappingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_nucleus_actor_id(self, workplace_user_id: str) -> int | None:
        row = await self._session.get(
            NucleusActorMappingORM, workplace_user_id
        )
        return row.nucleus_actor_id if row is not None else None
