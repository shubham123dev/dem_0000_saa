"""Organization adapter contract.

The service and API layers depend on this protocol, never directly on the
SQLite ORM or the mock backend. This keeps the mock database swappable for the
future ``NucleusOrganizationApiAdapter`` without changing callers.

Every method returns framework-agnostic **domain models** and performs no
Workplace-Agent permission enforcement — that is the service/permission layer's
responsibility. The gateway only reflects the state of the organization system
of record.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.domain.models import (
    OrganizationMember,
    OrganizationProfile,
    ReportAccessDecision,
    ReportWithAccess,
    SeatSummary,
)


@runtime_checkable
class OrganizationApiGateway(Protocol):
    """Replaceable gateway to an organization system of record.

    Step 0 requires only read operations. Write operations are defined as
    future mock-API contracts and are intentionally absent here.
    """

    async def get_profile(self, organization_id: str) -> OrganizationProfile:
        """Return the exact organization profile.

        Raises:
            OrganizationNotFoundError: when the organization does not exist.
        """
        ...

    async def list_members(self, organization_id: str) -> list[OrganizationMember]:
        """Return every membership in the organization, with derived seat status."""
        ...

    async def get_seat_summary(self, organization_id: str) -> SeatSummary:
        """Return computed seat entitlement vs. usage for the organization."""
        ...

    async def list_reports(self, organization_id: str) -> list[ReportWithAccess]:
        """Return the report catalog annotated with this org's access."""
        ...

    async def check_report_access(
        self, organization_id: str, report_id: str
    ) -> ReportAccessDecision:
        """Return the organization-level access decision for one report."""
        ...


# Backwards-compatible aliases — all names refer to the same contract.
OrganizationGateway = OrganizationApiGateway
OrganizationAdapter = OrganizationApiGateway
