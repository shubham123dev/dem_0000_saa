"""Organization repository: organization profile persistence."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.orm_models import OrganizationORM
from app.domain.enums import Environment, OrganizationStatus
from app.domain.models import OrganizationProfile


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
        contact_email: str,
    ) -> OrganizationProfile | None:
        row = await self._session.get(OrganizationORM, organization_id)
        if row is None:
            return None
        row.contact_email = contact_email
        row.version += 1
        await self._session.commit()
        await self._session.refresh(row)
        return self._to_domain(row)

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
