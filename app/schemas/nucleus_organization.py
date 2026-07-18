"""Stable HTTP contracts for the exact-schema Nucleus SQLite mock."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

from app.domain.nucleus_models import (
    NucleusCategoryAccess,
    NucleusCompanyProfileAccess,
    NucleusDrugAccess,
    NucleusIndicationAccess,
    NucleusMarketAccess,
    NucleusOrganizationAccount,
    NucleusOrganizationApprovalStatus,
    NucleusOrganizationEntitlements,
    NucleusOrganizationLicense,
    NucleusReportAccess,
    NucleusSpecialPermissions,
)
from app.schemas.organization import OrganizationAccessOut


class NucleusOrganizationAccountOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    organization_account_id: int
    organization_name: str
    organization_code: str | None = None
    organization_type: str | None = None
    industry: str | None = None
    website: str | None = None
    login_username: str
    email: str | None = None
    contact_person_name: str | None = None
    contact_person_designation: str | None = None
    contact_phone: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    postal_code: str | None = None
    status: str
    is_active: bool
    created_by: int | None = None
    created_date: datetime
    updated_by: int | None = None
    updated_date: datetime | None = None
    version: int = Field(ge=1)

    @classmethod
    def from_domain(
        cls,
        account: NucleusOrganizationAccount,
    ) -> "NucleusOrganizationAccountOut":
        return cls(**account.__dict__)


class NucleusOrganizationLicenseOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    organization_account_id: int
    max_user_limit: int = Field(ge=0)
    license_start_date: datetime | None = None
    license_end_date: datetime | None = None
    is_active: bool
    status: str
    version: int = Field(ge=1)

    @classmethod
    def from_domain(
        cls,
        license_info: NucleusOrganizationLicense,
    ) -> "NucleusOrganizationLicenseOut":
        return cls(**license_info.__dict__)


class NucleusOrganizationApprovalStatusOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    organization_account_id: int
    status: str
    approved_by: int | None = None
    approved_date: datetime | None = None
    rejected_by: int | None = None
    rejected_date: datetime | None = None
    rejection_reason: str | None = None
    is_active: bool
    version: int = Field(ge=1)

    @classmethod
    def from_domain(
        cls,
        approval: NucleusOrganizationApprovalStatus,
    ) -> "NucleusOrganizationApprovalStatusOut":
        return cls(**approval.__dict__)


class NucleusCategoryAccessOut(BaseModel):
    access_id: int
    organization_account_id: int
    category_id: int | None = None
    category_sample_id: int | None = None
    created_date: datetime | None = None
    is_active: bool
    version: int = Field(ge=1)

    @classmethod
    def from_domain(cls, value: NucleusCategoryAccess) -> "NucleusCategoryAccessOut":
        return cls(**value.__dict__)


class NucleusCompanyProfileAccessOut(BaseModel):
    access_id: int
    organization_account_id: int
    company_id: int | None = None
    version: int = Field(ge=1)

    @classmethod
    def from_domain(
        cls,
        value: NucleusCompanyProfileAccess,
    ) -> "NucleusCompanyProfileAccessOut":
        return cls(**value.__dict__)


class NucleusDrugAccessOut(BaseModel):
    access_id: int
    organization_account_id: int
    drug_id: int | None = None
    version: int = Field(ge=1)

    @classmethod
    def from_domain(cls, value: NucleusDrugAccess) -> "NucleusDrugAccessOut":
        return cls(**value.__dict__)


class NucleusIndicationAccessOut(BaseModel):
    access_id: int
    organization_account_id: int
    indication_id: int | None = None
    version: int = Field(ge=1)

    @classmethod
    def from_domain(
        cls,
        value: NucleusIndicationAccess,
    ) -> "NucleusIndicationAccessOut":
        return cls(**value.__dict__)


class NucleusMarketAccessOut(BaseModel):
    access_id: int
    organization_account_id: int
    market_id: int | None = None
    market_sample_id: int | None = None
    version: int = Field(ge=1)

    @classmethod
    def from_domain(cls, value: NucleusMarketAccess) -> "NucleusMarketAccessOut":
        return cls(**value.__dict__)


class NucleusReportAccessOut(BaseModel):
    access_id: int
    organization_account_id: int
    reports_id: int | None = None
    sample_id: int | None = None
    sample_toc_id: int | None = None
    speciality_id: int | None = None
    is_executive_access: bool | None = None
    created_date: datetime | None = None
    is_active: bool
    version: int = Field(ge=1)

    @classmethod
    def from_domain(cls, value: NucleusReportAccess) -> "NucleusReportAccessOut":
        return cls(**value.__dict__)


class NucleusSpecialPermissionsOut(BaseModel):
    permission_id: int
    organization_account_id: int
    cp_company_master_pharma_id: int | None = None
    hc_theropetic_category_pharma_id: int | None = None
    hc_theropetic_category_epidem_id: int | None = None
    hc_disease_code_epidem_id: int | None = None
    reports_custom_id: int | None = None
    importexport_report_id: int | None = None
    created_date: datetime | None = None
    is_active: bool
    version: int = Field(ge=1)

    @classmethod
    def from_domain(
        cls,
        value: NucleusSpecialPermissions,
    ) -> "NucleusSpecialPermissionsOut":
        return cls(**value.__dict__)


class NucleusOrganizationEntitlementsOut(BaseModel):
    organization_account_id: int
    category_access: tuple[NucleusCategoryAccessOut, ...]
    company_profile_access: tuple[NucleusCompanyProfileAccessOut, ...]
    drug_access: tuple[NucleusDrugAccessOut, ...]
    indication_access: tuple[NucleusIndicationAccessOut, ...]
    market_access: tuple[NucleusMarketAccessOut, ...]
    report_access: tuple[NucleusReportAccessOut, ...]
    special_permissions: tuple[NucleusSpecialPermissionsOut, ...]

    @classmethod
    def from_domain(
        cls,
        value: NucleusOrganizationEntitlements,
    ) -> "NucleusOrganizationEntitlementsOut":
        return cls(
            organization_account_id=value.organization_account_id,
            category_access=tuple(
                NucleusCategoryAccessOut.from_domain(item)
                for item in value.category_access
            ),
            company_profile_access=tuple(
                NucleusCompanyProfileAccessOut.from_domain(item)
                for item in value.company_profile_access
            ),
            drug_access=tuple(
                NucleusDrugAccessOut.from_domain(item) for item in value.drug_access
            ),
            indication_access=tuple(
                NucleusIndicationAccessOut.from_domain(item)
                for item in value.indication_access
            ),
            market_access=tuple(
                NucleusMarketAccessOut.from_domain(item)
                for item in value.market_access
            ),
            report_access=tuple(
                NucleusReportAccessOut.from_domain(item)
                for item in value.report_access
            ),
            special_permissions=tuple(
                NucleusSpecialPermissionsOut.from_domain(item)
                for item in value.special_permissions
            ),
        )


class NucleusAccountResponse(BaseModel):
    organization_id: str
    account: NucleusOrganizationAccountOut
    access: OrganizationAccessOut
    generated_at: datetime

    @classmethod
    def build(
        cls,
        *,
        organization_id: str,
        account: NucleusOrganizationAccount,
        access: OrganizationAccessOut,
    ) -> "NucleusAccountResponse":
        return cls(
            organization_id=organization_id,
            account=NucleusOrganizationAccountOut.from_domain(account),
            access=access,
            generated_at=datetime.now(timezone.utc),
        )


class NucleusLicenseResponse(BaseModel):
    organization_id: str
    license: NucleusOrganizationLicenseOut
    access: OrganizationAccessOut
    generated_at: datetime


class NucleusApprovalStatusResponse(BaseModel):
    organization_id: str
    approval: NucleusOrganizationApprovalStatusOut
    access: OrganizationAccessOut
    generated_at: datetime


class NucleusEntitlementsResponse(BaseModel):
    organization_id: str
    entitlements: NucleusOrganizationEntitlementsOut
    access: OrganizationAccessOut
    generated_at: datetime
