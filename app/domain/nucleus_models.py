"""Framework-neutral models for the exact-schema Nucleus SQLite mock."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class NucleusOrganizationAccount:
    organization_account_id: int
    organization_name: str
    organization_code: str | None
    organization_type: str | None
    industry: str | None
    website: str | None
    login_username: str
    email: str | None
    contact_person_name: str | None
    contact_person_designation: str | None
    contact_phone: str | None
    address_line1: str | None
    address_line2: str | None
    city: str | None
    state: str | None
    country: str | None
    postal_code: str | None
    status: str
    is_active: bool
    created_by: int | None
    created_date: datetime
    updated_by: int | None
    updated_date: datetime | None
    version: int


@dataclass(frozen=True)
class NucleusOrganizationLicense:
    organization_account_id: int
    max_user_limit: int
    license_start_date: datetime | None
    license_end_date: datetime | None
    is_active: bool
    status: str
    version: int


@dataclass(frozen=True)
class NucleusOrganizationApprovalStatus:
    organization_account_id: int
    status: str
    approved_by: int | None
    approved_date: datetime | None
    rejected_by: int | None
    rejected_date: datetime | None
    rejection_reason: str | None
    is_active: bool
    version: int


@dataclass(frozen=True)
class NucleusCategoryAccess:
    access_id: int
    organization_account_id: int
    category_id: int | None
    category_sample_id: int | None
    created_date: datetime | None
    is_active: bool
    version: int


@dataclass(frozen=True)
class NucleusCompanyProfileAccess:
    access_id: int
    organization_account_id: int
    company_id: int | None
    version: int


@dataclass(frozen=True)
class NucleusDrugAccess:
    access_id: int
    organization_account_id: int
    drug_id: int | None
    version: int


@dataclass(frozen=True)
class NucleusIndicationAccess:
    access_id: int
    organization_account_id: int
    indication_id: int | None
    version: int


@dataclass(frozen=True)
class NucleusMarketAccess:
    access_id: int
    organization_account_id: int
    market_id: int | None
    market_sample_id: int | None
    version: int


@dataclass(frozen=True)
class NucleusReportAccess:
    access_id: int
    organization_account_id: int
    reports_id: int | None
    sample_id: int | None
    sample_toc_id: int | None
    speciality_id: int | None
    is_executive_access: bool | None
    created_date: datetime | None
    is_active: bool
    version: int


@dataclass(frozen=True)
class NucleusSpecialPermissions:
    permission_id: int
    organization_account_id: int
    cp_company_master_pharma_id: int | None
    hc_theropetic_category_pharma_id: int | None
    hc_theropetic_category_epidem_id: int | None
    hc_disease_code_epidem_id: int | None
    reports_custom_id: int | None
    importexport_report_id: int | None
    created_date: datetime | None
    is_active: bool
    version: int


@dataclass(frozen=True)
class NucleusOrganizationEntitlements:
    organization_account_id: int
    category_access: tuple[NucleusCategoryAccess, ...]
    company_profile_access: tuple[NucleusCompanyProfileAccess, ...]
    drug_access: tuple[NucleusDrugAccess, ...]
    indication_access: tuple[NucleusIndicationAccess, ...]
    market_access: tuple[NucleusMarketAccess, ...]
    report_access: tuple[NucleusReportAccess, ...]
    special_permissions: tuple[NucleusSpecialPermissions, ...]
