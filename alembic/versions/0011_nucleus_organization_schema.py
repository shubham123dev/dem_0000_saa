"""add exact Nucleus organization schema mock tables

Revision ID: 0011_nucleus_organization_schema
Revises: 0010_add_organization_overview
Create Date: 2026-07-18
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011_nucleus_organization_schema"
down_revision: Union[str, None] = "0010_add_organization_overview"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "OrganizationAccount",
        sa.Column("OrganizationAccountId", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("OrganizationName", sa.String(length=250), nullable=False),
        sa.Column("OrganizationCode", sa.String(length=50), nullable=True),
        sa.Column("OrganizationType", sa.String(length=100), nullable=True),
        sa.Column("Industry", sa.String(length=150), nullable=True),
        sa.Column("Website", sa.String(length=250), nullable=True),
        sa.Column("UserName", sa.String(length=150), nullable=False),
        sa.Column("Password", sa.String(length=250), nullable=False),
        sa.Column("Email", sa.String(length=150), nullable=True),
        sa.Column("ContactPersonName", sa.String(length=150), nullable=True),
        sa.Column("ContactPersonDesignation", sa.String(length=150), nullable=True),
        sa.Column("ContactPhone", sa.String(length=50), nullable=True),
        sa.Column("AddressLine1", sa.String(length=250), nullable=True),
        sa.Column("AddressLine2", sa.String(length=250), nullable=True),
        sa.Column("City", sa.String(length=100), nullable=True),
        sa.Column("State", sa.String(length=100), nullable=True),
        sa.Column("Country", sa.String(length=100), nullable=True),
        sa.Column("PostalCode", sa.String(length=30), nullable=True),
        sa.Column("MaxUserLimit", sa.Integer(), nullable=False),
        sa.Column("LicenseStartDate", sa.DateTime(timezone=True), nullable=True),
        sa.Column("LicenseEndDate", sa.DateTime(timezone=True), nullable=True),
        sa.Column("Status", sa.String(length=30), nullable=False),
        sa.Column("ApprovedBy", sa.Integer(), nullable=True),
        sa.Column("ApprovedDate", sa.DateTime(timezone=True), nullable=True),
        sa.Column("RejectedBy", sa.Integer(), nullable=True),
        sa.Column("RejectedDate", sa.DateTime(timezone=True), nullable=True),
        sa.Column("RejectionReason", sa.String(length=500), nullable=True),
        sa.Column("IsActive", sa.Boolean(), nullable=False),
        sa.Column("CreatedBy", sa.Integer(), nullable=True),
        sa.Column("CreatedDate", sa.DateTime(timezone=True), nullable=False),
        sa.Column("UpdatedBy", sa.Integer(), nullable=True),
        sa.Column("UpdatedDate", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_nucleus_org_account_code", "OrganizationAccount", ["OrganizationCode"], unique=True)
    op.create_index("ix_nucleus_org_account_active_status", "OrganizationAccount", ["IsActive", "Status"])

    op.create_table(
        "OrganizationCategoryAccess",
        sa.Column("OrganizationCategoryAccessId", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("OrganizationAccountId", sa.Integer(), nullable=False),
        sa.Column("CategoryID", sa.Integer(), nullable=True),
        sa.Column("CategorySampleID", sa.Integer(), nullable=True),
        sa.Column("CreatedDate", sa.DateTime(timezone=True), nullable=True),
        sa.Column("IsActive", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["OrganizationAccountId"], ["OrganizationAccount.OrganizationAccountId"], ondelete="CASCADE"),
    )
    op.create_index("ix_nucleus_category_access_org_active", "OrganizationCategoryAccess", ["OrganizationAccountId", "IsActive"])

    op.create_table(
        "OrganizationCompanyProfileAccess",
        sa.Column("OrganizationCompanyProfileAccessId", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("OrganizationAccountId", sa.Integer(), nullable=False),
        sa.Column("CompanyID", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["OrganizationAccountId"], ["OrganizationAccount.OrganizationAccountId"], ondelete="CASCADE"),
    )
    op.create_index("ix_nucleus_company_access_org", "OrganizationCompanyProfileAccess", ["OrganizationAccountId"])

    op.create_table(
        "OrganizationDrugAccess",
        sa.Column("OrganizationDrugAccessId", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("OrganizationAccountId", sa.Integer(), nullable=False),
        sa.Column("DrugID", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["OrganizationAccountId"], ["OrganizationAccount.OrganizationAccountId"], ondelete="CASCADE"),
    )
    op.create_index("ix_nucleus_drug_access_org", "OrganizationDrugAccess", ["OrganizationAccountId"])

    op.create_table(
        "OrganizationIndicationAccess",
        sa.Column("OrganizationIndicationAccessId", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("OrganizationAccountId", sa.Integer(), nullable=False),
        sa.Column("IndicationID", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["OrganizationAccountId"], ["OrganizationAccount.OrganizationAccountId"], ondelete="CASCADE"),
    )
    op.create_index("ix_nucleus_indication_access_org", "OrganizationIndicationAccess", ["OrganizationAccountId"])

    op.create_table(
        "OrganizationMarketAccess",
        sa.Column("OrganizationMarketAccessId", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("OrganizationAccountId", sa.Integer(), nullable=False),
        sa.Column("MarketID", sa.Integer(), nullable=True),
        sa.Column("MarketSampleId", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["OrganizationAccountId"], ["OrganizationAccount.OrganizationAccountId"], ondelete="CASCADE"),
    )
    op.create_index("ix_nucleus_market_access_org", "OrganizationMarketAccess", ["OrganizationAccountId"])

    op.create_table(
        "OrganizationPermission",
        sa.Column("OrganizationPermissionId", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("OrganizationAccountId", sa.Integer(), nullable=False),
        sa.Column("cp_CompanyMaster_PharmaID", sa.Integer(), nullable=True),
        sa.Column("HC_TheropeticCategory_PharmaID", sa.Integer(), nullable=True),
        sa.Column("HC_TheropeticCategory_EpidemID", sa.Integer(), nullable=True),
        sa.Column("HC_Disease_Code_EpidemID", sa.Integer(), nullable=True),
        sa.Column("ReportsCustomID", sa.Integer(), nullable=True),
        sa.Column("importexportReportID", sa.Integer(), nullable=True),
        sa.Column("CreatedDate", sa.DateTime(timezone=True), nullable=True),
        sa.Column("IsActive", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["OrganizationAccountId"], ["OrganizationAccount.OrganizationAccountId"], ondelete="CASCADE"),
    )
    op.create_index("ix_nucleus_permission_org_active", "OrganizationPermission", ["OrganizationAccountId", "IsActive"])

    op.create_table(
        "OrganizationReportAccess",
        sa.Column("OrganizationReportAccessId", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("OrganizationAccountId", sa.Integer(), nullable=False),
        sa.Column("ReportsID", sa.Integer(), nullable=True),
        sa.Column("SampleID", sa.Integer(), nullable=True),
        sa.Column("SampleTocID", sa.Integer(), nullable=True),
        sa.Column("SpecialityID", sa.Integer(), nullable=True),
        sa.Column("IsExecutiveAccess", sa.Boolean(), nullable=True),
        sa.Column("CreatedDate", sa.DateTime(timezone=True), nullable=True),
        sa.Column("IsActive", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["OrganizationAccountId"], ["OrganizationAccount.OrganizationAccountId"], ondelete="CASCADE"),
    )
    op.create_index("ix_nucleus_report_access_org_active", "OrganizationReportAccess", ["OrganizationAccountId", "IsActive"])

    op.create_table(
        "nucleus_resource_versions",
        sa.Column("resource_type", sa.String(length=80), primary_key=True, nullable=False),
        sa.Column("resource_key", sa.String(length=200), primary_key=True, nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("resource_type", "resource_key", name="uq_nucleus_resource_version"),
    )


def downgrade() -> None:
    op.drop_table("nucleus_resource_versions")
    op.drop_index("ix_nucleus_report_access_org_active", table_name="OrganizationReportAccess")
    op.drop_table("OrganizationReportAccess")
    op.drop_index("ix_nucleus_permission_org_active", table_name="OrganizationPermission")
    op.drop_table("OrganizationPermission")
    op.drop_index("ix_nucleus_market_access_org", table_name="OrganizationMarketAccess")
    op.drop_table("OrganizationMarketAccess")
    op.drop_index("ix_nucleus_indication_access_org", table_name="OrganizationIndicationAccess")
    op.drop_table("OrganizationIndicationAccess")
    op.drop_index("ix_nucleus_drug_access_org", table_name="OrganizationDrugAccess")
    op.drop_table("OrganizationDrugAccess")
    op.drop_index("ix_nucleus_company_access_org", table_name="OrganizationCompanyProfileAccess")
    op.drop_table("OrganizationCompanyProfileAccess")
    op.drop_index("ix_nucleus_category_access_org_active", table_name="OrganizationCategoryAccess")
    op.drop_table("OrganizationCategoryAccess")
    op.drop_index("ix_nucleus_org_account_active_status", table_name="OrganizationAccount")
    op.drop_index("ix_nucleus_org_account_code", table_name="OrganizationAccount")
    op.drop_table("OrganizationAccount")
