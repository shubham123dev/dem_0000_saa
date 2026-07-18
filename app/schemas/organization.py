"""Organization API schemas."""

from __future__ import annotations

from datetime import date, datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import Environment, OrganizationStatus, WorkspaceHealthStatus
from app.domain.models import OrganizationOverview, OrganizationProfile


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: str
    display_name: str
    legal_name: str | None = None
    contact_email: str | None = None
    environment: Environment
    status: OrganizationStatus
    version: int

    @classmethod
    def from_profile(cls, profile: OrganizationProfile) -> "OrganizationOut":
        return cls(
            id=profile.id,
            display_name=profile.display_name,
            legal_name=profile.legal_name,
            contact_email=profile.contact_email,
            environment=profile.environment,
            status=profile.status,
            version=profile.version,
        )


class OrganizationOverviewOrganizationOut(OrganizationOut):
    organization_type: str
    renewal_date: date | None = None
    workspace_status: WorkspaceHealthStatus


class OrganizationOverviewMetricsOut(BaseModel):
    licensed_modules: int = Field(ge=0)
    available_areas: int = Field(ge=0)
    organization_logins: int = Field(ge=0)
    workspace_health_percent: int = Field(ge=0, le=100)


class OrganizationOverviewOut(BaseModel):
    """Stable wire contract consumed by both chat and the dashboard frontend."""

    organization: OrganizationOverviewOrganizationOut
    metrics: OrganizationOverviewMetricsOut
    overview_version: int = Field(ge=1)
    overview_updated_at: datetime | None = None

    @classmethod
    def from_domain(cls, overview: OrganizationOverview) -> "OrganizationOverviewOut":
        profile = overview.organization
        return cls(
            organization=OrganizationOverviewOrganizationOut(
                id=profile.id,
                display_name=profile.display_name,
                legal_name=profile.legal_name,
                contact_email=profile.contact_email,
                environment=profile.environment,
                status=profile.status,
                version=profile.version,
                organization_type=overview.organization_type,
                renewal_date=overview.renewal_date,
                workspace_status=overview.workspace_status,
            ),
            metrics=OrganizationOverviewMetricsOut(
                licensed_modules=overview.metrics.licensed_modules,
                available_areas=overview.metrics.available_areas,
                organization_logins=overview.metrics.organization_logins,
                workspace_health_percent=(
                    overview.metrics.workspace_health_percent
                ),
            ),
            overview_version=overview.version,
            overview_updated_at=overview.updated_at,
        )


class OrganizationAccessOut(BaseModel):
    user_id: str
    permission: str


class OrganizationProfileResponse(BaseModel):
    organization: OrganizationOut
    access: OrganizationAccessOut


class OrganizationOverviewResponse(OrganizationOverviewOut):
    access: OrganizationAccessOut
    generated_at: datetime

    @classmethod
    def from_domain(
        cls,
        overview: OrganizationOverview,
        *,
        access: OrganizationAccessOut,
    ) -> "OrganizationOverviewResponse":
        wire = OrganizationOverviewOut.from_domain(overview)
        return cls(
            **wire.model_dump(),
            access=access,
            generated_at=datetime.now(timezone.utc),
        )


class CapabilityActionOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    required_arguments: tuple[str, ...]
    risk_level: str
    requires_approval: bool
    supports_dry_run: bool
    minimum_approvals: int
    self_approval_allowed: bool


class CapabilitiesResponse(BaseModel):
    environment: str = "sandbox"
    read_tools: tuple[str, ...] = Field(
        default=(
            "get_organization_overview",
            "get_nucleus_organization_account",
            "get_nucleus_organization_license",
            "get_nucleus_organization_approval_status",
            "get_nucleus_organization_entitlements",
            "get_organization_profile",
            "list_organization_users",
            "get_organization_seat_summary",
            "list_organization_reports",
            "check_organization_report_access",
            "get_organization_audit_log",
        )
    )
    write_tools: tuple[str, ...] = ()
    write_actions: tuple[CapabilityActionOut, ...] = ()
    approval_required: bool = True
    production_access: bool = False
