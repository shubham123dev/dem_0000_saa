"""Mock organization adapter backed by the sandbox SQLite database.

This satisfies the ``OrganizationGateway`` contract. The future production
implementation, ``NucleusOrganizationApiAdapter``, will call the real Nucleus
organization API and is intentionally NOT implemented in Step 0.
"""

from __future__ import annotations

from app.core.errors import OrganizationNotFoundError
from app.domain.models import OrganizationProfile
from app.repositories.organization_repository import OrganizationRepository


class MockOrganizationAdapter:
    """Reads organization state from the mock database via a repository."""

    def __init__(self, organization_repository: OrganizationRepository) -> None:
        self._organizations = organization_repository

    async def get_profile(self, organization_id: str) -> OrganizationProfile:
        profile = await self._organizations.get_profile(organization_id)
        if profile is None:
            raise OrganizationNotFoundError()
        return profile
