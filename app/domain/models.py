"""Framework-agnostic domain models.

These dataclasses represent domain state passed between the persistence,
adapter, service, and API layers. Keeping them independent of both the ORM and
the Pydantic API schemas lets the adapter contract stay stable when the mock
database is later replaced by the real Nucleus organization API.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from app.domain.enums import (
    Environment,
    MembershipStatus,
    OrganizationStatus,
    ReportAccessLevel,
    ReportAccessStatus,
    ReportStatus,
    SeatType,
    UserStatus,
    WorkspaceHealthStatus,
)


@dataclass(frozen=True)
class OrganizationProfile:
    """The exact organization state returned by an OrganizationApiGateway."""

    id: str
    display_name: str
    legal_name: str | None
    contact_email: str | None
    environment: Environment
    status: OrganizationStatus
    version: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class OrganizationOverviewMetrics:
    """Backend-owned metrics displayed on the organization overview page."""

    licensed_modules: int
    available_areas: int
    organization_logins: int
    workspace_health_percent: int


@dataclass(frozen=True)
class OrganizationOverview:
    """Stable overview contract independent of the future Nucleus wire schema."""

    organization: OrganizationProfile
    organization_type: str
    renewal_date: date | None
    workspace_status: WorkspaceHealthStatus
    metrics: OrganizationOverviewMetrics
    version: int
    updated_at: datetime | None = None


@dataclass(frozen=True)
class User:
    """An authenticated mock user (internal employee) from the sandbox DB."""

    id: str
    display_name: str
    email: str
    status: UserStatus
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE


@dataclass(frozen=True)
class OrganizationMember:
    """A user's membership in an organization, plus derived seat status.

    ``users`` and ``seats`` are distinct: an active member may or may not
    occupy a licensed seat.
    """

    user_id: str
    display_name: str
    email: str
    user_status: UserStatus
    role: str
    membership_status: MembershipStatus
    has_active_seat: bool
    joined_at: datetime | None = None


@dataclass(frozen=True)
class SeatSummary:
    """Seat entitlement vs. consumption for one organization/seat type.

    ``used``/``available`` are always calculated from active seat assignments,
    never stored as a source of truth.
    """

    organization_id: str
    seat_type: SeatType
    total_seats: int
    active_assignments: int
    available_seats: int
    seated_user_ids: tuple[str, ...]


@dataclass(frozen=True)
class Report:
    """A catalog report. ``external_report_id`` maps to the future real system."""

    id: str
    external_report_id: str
    title: str
    market_name: str | None
    status: ReportStatus


@dataclass(frozen=True)
class ReportWithAccess:
    """A catalog report annotated with this organization's access."""

    report: Report
    has_access: bool
    access_level: ReportAccessLevel | None
    access_status: ReportAccessStatus | None


@dataclass(frozen=True)
class ReportAccessDecision:
    """The resolved organization-level access decision for one report."""

    organization_id: str
    report_id: str
    has_access: bool
    access_level: ReportAccessLevel | None
    access_status: ReportAccessStatus | None


@dataclass(frozen=True)
class AuditEvent:
    """An append-only record of a read or controlled action."""

    id: str
    actor_user_id: str
    organization_id: str
    event_type: str
    operation: str
    outcome: str
    resource_type: str
    resource_id: str
    details_json: dict | None
    created_at: datetime | None = None
