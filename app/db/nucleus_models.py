"""SQLite ORM models mirroring the supplied Nucleus organization schema.

The eight PascalCase tables and their column names intentionally match the
schema supplied by the product team. ``nucleus_resource_versions`` is an
internal Workplace Agent sidecar used only for optimistic concurrency; it is
not part of the future Nucleus wire contract.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class NucleusOrganizationAccountORM(Base):
    __tablename__ = "OrganizationAccount"
    __table_args__ = (
        Index("ix_nucleus_org_account_code", "OrganizationCode", unique=True),
        Index("ix_nucleus_org_account_active_status", "IsActive", "Status"),
    )

    organization_account_id: Mapped[int] = mapped_column(
        "OrganizationAccountId", Integer, primary_key=True, autoincrement=True
    )
    organization_name: Mapped[str] = mapped_column(
        "OrganizationName", String(250), nullable=False
    )
    organization_code: Mapped[str | None] = mapped_column(
        "OrganizationCode", String(50), nullable=True
    )
    organization_type: Mapped[str | None] = mapped_column(
        "OrganizationType", String(100), nullable=True
    )
    industry: Mapped[str | None] = mapped_column("Industry", String(150), nullable=True)
    website: Mapped[str | None] = mapped_column("Website", String(250), nullable=True)
    user_name: Mapped[str] = mapped_column("UserName", String(150), nullable=False)
    password: Mapped[str] = mapped_column("Password", String(250), nullable=False)
    email: Mapped[str | None] = mapped_column("Email", String(150), nullable=True)
    contact_person_name: Mapped[str | None] = mapped_column(
        "ContactPersonName", String(150), nullable=True
    )
    contact_person_designation: Mapped[str | None] = mapped_column(
        "ContactPersonDesignation", String(150), nullable=True
    )
    contact_phone: Mapped[str | None] = mapped_column(
        "ContactPhone", String(50), nullable=True
    )
    address_line1: Mapped[str | None] = mapped_column(
        "AddressLine1", String(250), nullable=True
    )
    address_line2: Mapped[str | None] = mapped_column(
        "AddressLine2", String(250), nullable=True
    )
    city: Mapped[str | None] = mapped_column("City", String(100), nullable=True)
    state: Mapped[str | None] = mapped_column("State", String(100), nullable=True)
    country: Mapped[str | None] = mapped_column("Country", String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(
        "PostalCode", String(30), nullable=True
    )
    max_user_limit: Mapped[int] = mapped_column("MaxUserLimit", Integer, nullable=False)
    license_start_date: Mapped[datetime | None] = mapped_column(
        "LicenseStartDate", DateTime(timezone=True), nullable=True
    )
    license_end_date: Mapped[datetime | None] = mapped_column(
        "LicenseEndDate", DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column("Status", String(30), nullable=False)
    approved_by: Mapped[int | None] = mapped_column("ApprovedBy", Integer, nullable=True)
    approved_date: Mapped[datetime | None] = mapped_column(
        "ApprovedDate", DateTime(timezone=True), nullable=True
    )
    rejected_by: Mapped[int | None] = mapped_column("RejectedBy", Integer, nullable=True)
    rejected_date: Mapped[datetime | None] = mapped_column(
        "RejectedDate", DateTime(timezone=True), nullable=True
    )
    rejection_reason: Mapped[str | None] = mapped_column(
        "RejectionReason", String(500), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        "IsActive", Boolean, nullable=False, default=True
    )
    created_by: Mapped[int | None] = mapped_column("CreatedBy", Integer, nullable=True)
    created_date: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_by: Mapped[int | None] = mapped_column("UpdatedBy", Integer, nullable=True)
    updated_date: Mapped[datetime | None] = mapped_column(
        "UpdatedDate", DateTime(timezone=True), nullable=True
    )


class NucleusOrganizationCategoryAccessORM(Base):
    __tablename__ = "OrganizationCategoryAccess"
    __table_args__ = (
        Index("ix_nucleus_category_access_org_active", "OrganizationAccountId", "IsActive"),
    )

    organization_category_access_id: Mapped[int] = mapped_column(
        "OrganizationCategoryAccessId", Integer, primary_key=True, autoincrement=True
    )
    organization_account_id: Mapped[int] = mapped_column(
        "OrganizationAccountId",
        Integer,
        ForeignKey("OrganizationAccount.OrganizationAccountId", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[int | None] = mapped_column("CategoryID", Integer, nullable=True)
    category_sample_id: Mapped[int | None] = mapped_column(
        "CategorySampleID", Integer, nullable=True
    )
    created_date: Mapped[datetime | None] = mapped_column(
        "CreatedDate", DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        "IsActive", Boolean, nullable=False, default=True
    )


class NucleusOrganizationCompanyProfileAccessORM(Base):
    __tablename__ = "OrganizationCompanyProfileAccess"
    __table_args__ = (
        Index("ix_nucleus_company_access_org", "OrganizationAccountId"),
    )

    organization_company_profile_access_id: Mapped[int] = mapped_column(
        "OrganizationCompanyProfileAccessId",
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    organization_account_id: Mapped[int] = mapped_column(
        "OrganizationAccountId",
        Integer,
        ForeignKey("OrganizationAccount.OrganizationAccountId", ondelete="CASCADE"),
        nullable=False,
    )
    company_id: Mapped[int | None] = mapped_column("CompanyID", Integer, nullable=True)


class NucleusOrganizationDrugAccessORM(Base):
    __tablename__ = "OrganizationDrugAccess"
    __table_args__ = (Index("ix_nucleus_drug_access_org", "OrganizationAccountId"),)

    organization_drug_access_id: Mapped[int] = mapped_column(
        "OrganizationDrugAccessId", Integer, primary_key=True, autoincrement=True
    )
    organization_account_id: Mapped[int] = mapped_column(
        "OrganizationAccountId",
        Integer,
        ForeignKey("OrganizationAccount.OrganizationAccountId", ondelete="CASCADE"),
        nullable=False,
    )
    drug_id: Mapped[int | None] = mapped_column("DrugID", Integer, nullable=True)


class NucleusOrganizationIndicationAccessORM(Base):
    __tablename__ = "OrganizationIndicationAccess"
    __table_args__ = (Index("ix_nucleus_indication_access_org", "OrganizationAccountId"),)

    organization_indication_access_id: Mapped[int] = mapped_column(
        "OrganizationIndicationAccessId", Integer, primary_key=True, autoincrement=True
    )
    organization_account_id: Mapped[int] = mapped_column(
        "OrganizationAccountId",
        Integer,
        ForeignKey("OrganizationAccount.OrganizationAccountId", ondelete="CASCADE"),
        nullable=False,
    )
    indication_id: Mapped[int | None] = mapped_column(
        "IndicationID", Integer, nullable=True
    )


class NucleusOrganizationMarketAccessORM(Base):
    __tablename__ = "OrganizationMarketAccess"
    __table_args__ = (Index("ix_nucleus_market_access_org", "OrganizationAccountId"),)

    organization_market_access_id: Mapped[int] = mapped_column(
        "OrganizationMarketAccessId", Integer, primary_key=True, autoincrement=True
    )
    organization_account_id: Mapped[int] = mapped_column(
        "OrganizationAccountId",
        Integer,
        ForeignKey("OrganizationAccount.OrganizationAccountId", ondelete="CASCADE"),
        nullable=False,
    )
    market_id: Mapped[int | None] = mapped_column("MarketID", Integer, nullable=True)
    market_sample_id: Mapped[int | None] = mapped_column(
        "MarketSampleId", Integer, nullable=True
    )


class NucleusOrganizationPermissionORM(Base):
    __tablename__ = "OrganizationPermission"
    __table_args__ = (
        Index("ix_nucleus_permission_org_active", "OrganizationAccountId", "IsActive"),
    )

    organization_permission_id: Mapped[int] = mapped_column(
        "OrganizationPermissionId", Integer, primary_key=True, autoincrement=True
    )
    organization_account_id: Mapped[int] = mapped_column(
        "OrganizationAccountId",
        Integer,
        ForeignKey("OrganizationAccount.OrganizationAccountId", ondelete="CASCADE"),
        nullable=False,
    )
    cp_company_master_pharma_id: Mapped[int | None] = mapped_column(
        "cp_CompanyMaster_PharmaID", Integer, nullable=True
    )
    hc_theropetic_category_pharma_id: Mapped[int | None] = mapped_column(
        "HC_TheropeticCategory_PharmaID", Integer, nullable=True
    )
    hc_theropetic_category_epidem_id: Mapped[int | None] = mapped_column(
        "HC_TheropeticCategory_EpidemID", Integer, nullable=True
    )
    hc_disease_code_epidem_id: Mapped[int | None] = mapped_column(
        "HC_Disease_Code_EpidemID", Integer, nullable=True
    )
    reports_custom_id: Mapped[int | None] = mapped_column(
        "ReportsCustomID", Integer, nullable=True
    )
    importexport_report_id: Mapped[int | None] = mapped_column(
        "importexportReportID", Integer, nullable=True
    )
    created_date: Mapped[datetime | None] = mapped_column(
        "CreatedDate", DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        "IsActive", Boolean, nullable=False, default=True
    )


class NucleusOrganizationReportAccessORM(Base):
    __tablename__ = "OrganizationReportAccess"
    __table_args__ = (
        Index("ix_nucleus_report_access_org_active", "OrganizationAccountId", "IsActive"),
    )

    organization_report_access_id: Mapped[int] = mapped_column(
        "OrganizationReportAccessId", Integer, primary_key=True, autoincrement=True
    )
    organization_account_id: Mapped[int] = mapped_column(
        "OrganizationAccountId",
        Integer,
        ForeignKey("OrganizationAccount.OrganizationAccountId", ondelete="CASCADE"),
        nullable=False,
    )
    reports_id: Mapped[int | None] = mapped_column("ReportsID", Integer, nullable=True)
    sample_id: Mapped[int | None] = mapped_column("SampleID", Integer, nullable=True)
    sample_toc_id: Mapped[int | None] = mapped_column("SampleTocID", Integer, nullable=True)
    speciality_id: Mapped[int | None] = mapped_column(
        "SpecialityID", Integer, nullable=True
    )
    is_executive_access: Mapped[bool | None] = mapped_column(
        "IsExecutiveAccess", Boolean, nullable=True
    )
    created_date: Mapped[datetime | None] = mapped_column(
        "CreatedDate", DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        "IsActive", Boolean, nullable=False, default=True
    )


class NucleusResourceVersionORM(Base):
    """Internal version sidecar for exact-schema rows that have no version column."""

    __tablename__ = "nucleus_resource_versions"
    __table_args__ = (
        UniqueConstraint("resource_type", "resource_key", name="uq_nucleus_resource_version"),
    )

    resource_type: Mapped[str] = mapped_column(String(80), primary_key=True)
    resource_key: Mapped[str] = mapped_column(String(200), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )
