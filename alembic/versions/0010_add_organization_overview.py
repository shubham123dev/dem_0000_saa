"""Add the stable organization-overview sandbox contract.

Revision ID: 0010_add_organization_overview
Revises: 0009_operational_hardening
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010_add_organization_overview"
down_revision: Union[str, None] = "0009_operational_hardening"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organization_overviews",
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column(
            "organization_type",
            sa.String(length=64),
            nullable=False,
            server_default=sa.text("'organization'"),
        ),
        sa.Column("renewal_date", sa.Date(), nullable=True),
        sa.Column(
            "workspace_status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'unknown'"),
        ),
        sa.Column(
            "workspace_health_percent",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "licensed_modules",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "available_areas",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "organization_logins",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "workspace_status IN ('healthy', 'degraded', 'unavailable', 'unknown')",
            name="ck_org_overview_workspace_status",
        ),
        sa.CheckConstraint(
            "workspace_health_percent >= 0 AND workspace_health_percent <= 100",
            name="ck_org_overview_health_percent",
        ),
        sa.CheckConstraint(
            "licensed_modules >= 0",
            name="ck_org_overview_licensed_modules_nonnegative",
        ),
        sa.CheckConstraint(
            "available_areas >= 0",
            name="ck_org_overview_available_areas_nonnegative",
        ),
        sa.CheckConstraint(
            "organization_logins >= 0",
            name="ck_org_overview_logins_nonnegative",
        ),
        sa.CheckConstraint(
            "version >= 1",
            name="ck_org_overview_version_positive",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("organization_id"),
    )


def downgrade() -> None:
    op.drop_table("organization_overviews")
