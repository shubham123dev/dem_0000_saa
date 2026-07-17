"""Organization API schemas."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import Environment, OrganizationStatus
from app.domain.models import OrganizationProfile


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


class OrganizationAccessOut(BaseModel):
    user_id: str
    permission: str


class OrganizationProfileResponse(BaseModel):
    organization: OrganizationOut
    access: OrganizationAccessOut


class CapabilityActionOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    required_arguments: tuple[str, ...]
    risk_level: str
    requires_approval: bool
    supports_dry_run: bool


class CapabilitiesResponse(BaseModel):
    environment: str = "sandbox"
    read_tools: tuple[str, ...] = Field(
        default=(
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
