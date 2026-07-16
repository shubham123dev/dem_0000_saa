"""Organization adapter contract.

The service and API layers depend on this protocol, never directly on the
SQLite ORM. This keeps the mock database swappable for the future
``NucleusOrganizationApiAdapter`` without changing callers.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.domain.models import OrganizationProfile


@runtime_checkable
class OrganizationGateway(Protocol):
    """Replaceable gateway to an organization system of record.

    Step 0 requires only a single read operation.
    """

    async def get_profile(self, organization_id: str) -> OrganizationProfile:
        """Return the exact organization profile.

        Raises:
            OrganizationNotFoundError: when the organization does not exist.
        """
        ...


# Backwards-compatible alias — both names refer to the same contract.
OrganizationAdapter = OrganizationGateway
