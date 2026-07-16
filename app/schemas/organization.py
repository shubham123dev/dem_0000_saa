"""Organization API schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import Environment, OrganizationStatus
from app.domain.models import OrganizationProfile


class OrganizationOut(BaseModel):
    """Public organization profile representation.

    This is intentionally decoupled from the ORM: internal ORM objects are
    never exposed directly.
    """

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
    """The access context under which a read tool was invoked."""

    user_id: str
    permission: str


class OrganizationProfileResponse(BaseModel):
    """Response body for the profile read endpoint."""

    organization: OrganizationOut
    access: OrganizationAccessOut


class CapabilitiesResponse(BaseModel):
    """Advertised Step 0 capabilities. Zero write tools; no production access."""

    environment: str = "sandbox"
    read_tools: list[str] = Field(
        default_factory=lambda: [
            "get_organization_profile",
            "list_organization_users",
            "get_organization_seat_summary",
            "list_organization_reports",
            "check_organization_report_access",
        ]
    )
    write_tools: list[str] = Field(default_factory=list)
    production_access: bool = False
