"""Organization repository: organization profile persistence."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.orm_models import OrganizationORM
from app.domain.enums import Environment, OrganizationStatus
from app.domain.models import OrganizationProfile


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OrganizationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_profile(self, organization_id: str) -> OrganizationProfile | None:
        row = await self._session.get(OrganizationORM, organization_id)
        if row is None:
            return None
        return self._to_domain(row)

    async def update_contact_email(
        self,
        organization_id: str,
        contact_email: str | None,
    ) -> OrganizationProfile | None:
        row = await self._session.get(OrganizationORM, organization_id)
        if row is None:
            return None
        row.contact_email = contact_email
        row.version += 1
        row.updated_at = _utcnow()
        await self._session.commit()
        await self._session.refresh(row)
        return self._to_domain(row)

    async def update_contact_email_if_version(
        self,
        organization_id: str,
        contact_email: str | None,
        expected_version: int,
    ) -> OrganizationProfile | None:
        return await self._update_profile_if_version(
            organization_id=organization_id,
            expected_version=expected_version,
            values={"contact_email": contact_email},
        )

    async def update_display_name_if_version(
        self,
        organization_id: str,
        display_name: str,
        expected_version: int,
    ) -> OrganizationProfile | None:
        return await self._update_profile_if_version(
            organization_id=organization_id,
            expected_version=expected_version,
            values={"display_name": display_name},
        )

    async def _update_profile_if_version(
        self,
        *,
        organization_id: str,
        expected_version: int,
        values: dict,
    ) -> OrganizationProfile | None:
        statement = (
            update(OrganizationORM)
            .where(
                OrganizationORM.id == organization_id,
                OrganizationORM.version == expected_version,
            )
            .values(
                **values,
                version=expected_version + 1,
                updated_at=_utcnow(),
            )
        )
        result = await self._session.execute(statement)
        if result.rowcount != 1:
            await self._session.rollback()
            return None
        await self._session.commit()
        row = await self._session.get(OrganizationORM, organization_id)
        return self._to_domain(row) if row is not None else None

    @staticmethod
    def _to_domain(row: OrganizationORM) -> OrganizationProfile:
        return OrganizationProfile(
            id=row.id,
            display_name=row.display_name,
            legal_name=row.legal_name,
            contact_email=row.contact_email,
            environment=Environment(row.environment),
            status=OrganizationStatus(row.status),
            version=row.version,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
